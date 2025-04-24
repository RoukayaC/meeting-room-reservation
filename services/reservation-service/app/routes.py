from flask import Blueprint, request, jsonify, current_app, g
from .models import db, Reservation, ReservationStatus, ReservationAttendee
import requests, json
from datetime import datetime
from functools import wraps

reservation_bp = Blueprint('reservation', __name__, url_prefix='/api/reservations')

# --- UTILITY DECORATORS ---
def require_roles(roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            try:
                resp = requests.get(
                    f"{current_app.config['USER_SERVICE_URL']}/api/auth/validate",
                    headers={'Authorization': f'Bearer {token}'}
                )
                if resp.status_code != 200:
                    return jsonify(create_error_response("Invalid token", "UNAUTHORIZED")), 401
                g.user = resp.json()
                if roles and g.user.get('role') not in roles:
                    return jsonify({'error': f"{roles} access required"}), 403
            except requests.RequestException:
                return jsonify({'error': 'Auth service unavailable'}), 503
            return f(*args, **kwargs)
        return decorated
    return wrapper

auth_required = require_roles([])
admin_required = require_roles(['admin'])
employee_required = require_roles(['admin', 'employee'])

# --- UTILITY HELPERS ---
def create_error_response(message, error_code):
    """Helper function to create standardized error responses"""
    return {
        "error": message,
        "code": error_code
    }

def parse_date_safe(date_str, end_of_day=False):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if end_of_day:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        return None

def fetch_attendees(res_id):
    return [a.to_dict() for a in ReservationAttendee.query.filter_by(reservation_id=res_id)]

def fetch_room(room_id):
    try:
        res = requests.get(f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{room_id}")
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None

def check_room_availability(room_id, start_time, end_time):
    """Check with room service if the room is available"""
    try:
        resp = requests.get(
            f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/availability",
            params={
                'room_id': room_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        )
        if resp.status_code == 200:
            return True
        return False
    except requests.RequestException:
        current_app.logger.warning(f"Failed to check room availability with room service")
        return False  # Assume not available if service is down

# --- RESERVATION ROUTES ---
@reservation_bp.route('/', methods=['GET'])
@auth_required
def list_reservations():
    """Get all reservations (admin) or user's reservations"""
    # Admins can see all reservations, others only see their own
    query = Reservation.query
    if g.user['role'] != 'admin':
        query = query.filter_by(user_id=g.user['id'])
    
    # Filter by status if provided
    status = request.args.get('status')
    if status:
        try:
            status_enum = ReservationStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            pass  # Invalid status, ignore filter
    
    # Filter by date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        start_dt = parse_date_safe(start_date)
        if start_dt:
            query = query.filter(Reservation.start_time >= start_dt)
    
    if end_date:
        end_dt = parse_date_safe(end_date, end_of_day=True)
        if end_dt:
            query = query.filter(Reservation.end_time <= end_dt)
    
    # Execute query with ordering
    reservations = query.order_by(Reservation.start_time).all()
    return jsonify([r.to_dict() for r in reservations]), 200

@reservation_bp.route('/<int:reservation_id>', methods=['GET'])
@auth_required
def get_reservation(reservation_id):
    """Get a specific reservation"""
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Check permissions - only admin or the reservation owner can access
    if g.user['id'] != reservation.user_id and g.user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    res_dict = reservation.to_dict()
    res_dict['room'] = fetch_room(reservation.room_id)
    res_dict['attendees'] = fetch_attendees(reservation.id)
    
    return jsonify(res_dict), 200

@reservation_bp.route('/', methods=['POST'])
@auth_required
def create_reservation():
    """Create a new reservation"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_id', 'title', 'start_time', 'end_time']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Missing required field: {field}"}), 400
    
    # Parse dates
    try:
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400
    
    # Validate dates
    now = datetime.utcnow()
    if start_time < now:
        return jsonify({'error': "Cannot create reservation in the past"}), 400
    
    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400
    
    # Check if room is available
    if not check_room_availability(data['room_id'], start_time, end_time):
        return jsonify({'error': "Room is not available for the requested time"}), 409
    
    # Create reservation
    reservation = Reservation(
        room_id=data['room_id'],
        user_id=g.user['id'],
        title=data['title'],
        description=data.get('description', ''),
        start_time=start_time,
        end_time=end_time,
        status=ReservationStatus.CONFIRMED
    )
    
    # Add attendees if provided
    attendees = data.get('attendees', [])
    attendees_count = len(attendees) if attendees else 1  # Default to 1 (the creator)
    
    # Always include creator as an attendee if not in the list
    creator_in_list = False
    for attendee in attendees:
        if attendee.get('email') == g.user.get('email'):
            creator_in_list = True
            break
    
    if not creator_in_list and g.user.get('email'):
        attendees.append({
            'email': g.user['email'],
            'name': g.user.get('name', ''),
            'user_id': g.user['id']
        })
        attendees_count = len(attendees)
    
    reservation.attendees_count = attendees_count
    
    db.session.add(reservation)
    db.session.commit()
    
    # Add attendees after saving reservation to get its ID
    for attendee_data in attendees:
        if 'email' not in attendee_data:
            continue
        
        attendee = ReservationAttendee(
            reservation_id=reservation.id,
            user_id=attendee_data.get('user_id'),
            email=attendee_data['email'],
            name=attendee_data.get('name', '')
        )
        db.session.add(attendee)
    
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'reservation-events',
            key=str(reservation.id),
            value=json.dumps({
                'event': 'reservation_created',
                'reservation_id': reservation.id,
                'room_id': reservation.room_id,
                'user_id': reservation.user_id,
                'start_time': reservation.start_time.isoformat(),
                'end_time': reservation.end_time.isoformat()
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    # Return the reservation with attendees
    res_dict = reservation.to_dict()
    res_dict['attendees'] = fetch_attendees(reservation.id)
    
    return jsonify(res_dict), 201

@reservation_bp.route('/<int:reservation_id>', methods=['PUT'])
@auth_required
def update_reservation(reservation_id):
    """Update a reservation"""
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Only owner or admin can update
    if g.user['id'] != reservation.user_id and g.user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Cannot update cancelled/completed reservations
    if reservation.status in [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED]:
        return jsonify({'error': f"Cannot update {reservation.status.value} reservation"}), 400
    
    data = request.get_json()
    
    # Update basic fields
    if 'title' in data:
        reservation.title = data['title']
    if 'description' in data:
        reservation.description = data['description']
    
    # Handle date/time updates
    start_time = reservation.start_time
    end_time = reservation.end_time
    
    if 'start_time' in data:
        try:
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': "Invalid start_time format"}), 400
    
    if 'end_time' in data:
        try:
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': "Invalid end_time format"}), 400
    
    # Validate new times
    now = datetime.utcnow()
    if start_time < now:
        return jsonify({'error': "Cannot set start time in the past"}), 400
    
    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400
    
    # Check availability if time changed
    if (start_time != reservation.start_time or end_time != reservation.end_time):
        if not check_room_availability(reservation.room_id, start_time, end_time):
            return jsonify({'error': "Room is not available for the requested time"}), 409
        
        reservation.start_time = start_time
        reservation.end_time = end_time
    
    # Update attendees if provided
    if 'attendees' in data and isinstance(data['attendees'], list):
        # Remove existing attendees
        ReservationAttendee.query.filter_by(reservation_id=reservation.id).delete()
        
        # Add new attendees
        attendees = data['attendees']
        for attendee_data in attendees:
            if 'email' not in attendee_data:
                continue
            
            attendee = ReservationAttendee(
                reservation_id=reservation.id,
                user_id=attendee_data.get('user_id'),
                email=attendee_data['email'],
                name=attendee_data.get('name', '')
            )
            db.session.add(attendee)
        
        reservation.attendees_count = len(attendees)
    
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'reservation-events',
            key=str(reservation.id),
            value=json.dumps({
                'event': 'reservation_updated',
                'reservation_id': reservation.id,
                'room_id': reservation.room_id,
                'user_id': reservation.user_id
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    # Return updated reservation with attendees
    res_dict = reservation.to_dict()
    res_dict['attendees'] = fetch_attendees(reservation.id)
    
    return jsonify(res_dict), 200

@reservation_bp.route('/<int:reservation_id>', methods=['DELETE'])
@auth_required
def cancel_reservation(reservation_id):
    """Cancel a reservation"""
    reservation = db.session.get(Reservation, reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Only owner or admin can cancel
    if g.user['id'] != reservation.user_id and g.user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Cannot cancel completed reservations
    if reservation.status == ReservationStatus.COMPLETED:
        return jsonify({'error': "Cannot cancel completed reservation"}), 400
    
    # Cannot cancel reservations that already started
    if reservation.start_time <= datetime.utcnow():
        return jsonify({'error': "Cannot cancel a reservation that has already started"}), 400
    
    # Update status to cancelled
    reservation.status = ReservationStatus.CANCELLED
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'reservation-events',
            key=str(reservation.id),
            value=json.dumps({
                'event': 'reservation_cancelled',
                'reservation_id': reservation.id,
                'room_id': reservation.room_id,
                'user_id': reservation.user_id
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify({'message': 'Reservation cancelled successfully'}), 200

@reservation_bp.route('/user/<int:user_id>', methods=['GET'])
@auth_required
def get_user_reservations(user_id):
    """Get all reservations for a specific user"""
    # Check permissions - only admin or the user themselves can access
    if g.user['id'] != user_id and g.user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    reservations = Reservation.query.filter_by(user_id=user_id).order_by(Reservation.start_time).all()
    return jsonify([r.to_dict() for r in reservations]), 200

@reservation_bp.route('/room/<int:room_id>', methods=['GET'])
@auth_required
def get_room_reservations(room_id):
    """Get all reservations for a specific room"""
    # Get query parameters for date filtering
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Start with all reservations for the room
    query = Reservation.query.filter_by(room_id=room_id)
    
    # Filter by date range if provided
    if start_date:
        start_dt = parse_date_safe(start_date)
        if start_dt:
            query = query.filter(Reservation.end_time >= start_dt)
    
    if end_date:
        end_dt = parse_date_safe(end_date, end_of_day=True)
        if end_dt:
            query = query.filter(Reservation.start_time <= end_dt)
    
    # Filter by status
    query = query.filter(Reservation.status != ReservationStatus.CANCELLED)
    
    # Execute query
    reservations = query.order_by(Reservation.start_time).all()
    return jsonify([r.to_dict() for r in reservations]), 200

@reservation_bp.route('/check', methods=['GET'])
def check_reservation():
    """Check if a room is available for a specific time period"""
    # Get query parameters
    room_id = request.args.get('room_id', type=int)
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    
    if not room_id or not start_time_str or not end_time_str:
        return jsonify({'error': "room_id, start_time, and end_time are required"}), 400
    
    # Parse dates
    try:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400
    
    # Validate dates
    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400
    
    # Check for conflicting reservations
    conflicts = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status != ReservationStatus.CANCELLED,
        ((Reservation.start_time <= start_time) & (Reservation.end_time > start_time)) |
        ((Reservation.start_time < end_time) & (Reservation.end_time >= end_time)) |
        ((Reservation.start_time >= start_time) & (Reservation.end_time <= end_time))
    ).first()
    
    # Return availability
    available = conflicts is None
    return jsonify({'available': available}), 200