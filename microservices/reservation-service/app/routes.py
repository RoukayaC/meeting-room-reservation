from flask import Blueprint, request, jsonify, current_app, g
from .models import db, Reservation, ReservationStatus, ReservationAttendee
import requests
import jwt
from datetime import datetime, timedelta
import json
from functools import wraps
from sqlalchemy import or_

reservation_bp = Blueprint('reservation', __name__, url_prefix='/api/reservations')


def auth_required(f):
    """Decorator to require authentication by validating token with user service"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Authentication required'}), 401

        # Validate token with user service
        try:
            response = requests.get(
                f"{current_app.config['USER_SERVICE_URL']}/api/auth/validate",
                headers={'Authorization': f"Bearer {token}"}
            )

            if response.status_code != 200:
                return jsonify({'error': 'Invalid token'}), 401

            # Store user info in g
            g.user = response.json()
        except requests.RequestException:
            current_app.logger.error("Failed to validate token with user service")
            return jsonify({'error': 'Authentication service unavailable'}), 503

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user') or g.user.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated


def employee_required(f):
    """Decorator to require employee role (or admin)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user') or (g.user.get('role') not in ['employee', 'admin']):
            return jsonify({'error': 'Employee privileges required'}), 403
        return f(*args, **kwargs)
    return decorated


@reservation_bp.route('/', methods=['GET'])
@auth_required
def get_reservations():
    """Get reservations with filtering options"""
    # Get query parameters
    room_id = request.args.get('room_id', type=int)
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Build query
    query = Reservation.query

    # Apply filters
    if room_id:
        query = query.filter(Reservation.room_id == room_id)

    # For non-admins, limit to their own reservations unless a room_id is provided
    if g.user.get('role') != 'admin':
        if user_id and user_id != g.user.get('id'):
            return jsonify({'error': 'You can only view your own reservations'}), 403
        else:
            query = query.filter(Reservation.user_id == g.user.get('id'))
    elif user_id:  # Admin can filter by any user
        query = query.filter(Reservation.user_id == user_id)

    # Filter by status
    if status:
        try:
            status_enum = ReservationStatus(status)
            query = query.filter(Reservation.status == status_enum)
        except ValueError:
            valid_statuses = [s.value for s in ReservationStatus]
            return jsonify({'error': f"Invalid status. Must be one of: {valid_statuses}"}), 400

    # Filter by date range
    if start_date:
        try:
            start_date_parsed = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Reservation.start_time >= start_date_parsed)
        except ValueError:
            return jsonify({'error': "Invalid start_date format. Use ISO format (YYYY-MM-DD)"}), 400

    if end_date:
        try:
            end_date_parsed = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            # Include the whole day
            end_date_parsed = end_date_parsed.replace(hour=23, minute=59, second=59)
            query = query.filter(Reservation.end_time <= end_date_parsed)
        except ValueError:
            return jsonify({'error': "Invalid end_date format. Use ISO format (YYYY-MM-DD)"}), 400

    # Order by start time, most recent first
    query = query.order_by(Reservation.start_time.desc())

    reservations = query.all()
    result = []
    for reservation in reservations:
        res_dict = reservation.to_dict()

        # Get room details
        try:
            room_response = requests.get(
                f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{reservation.room_id}"
            )
            if room_response.status_code == 200:
                res_dict['room'] = room_response.json()
        except requests.RequestException:
            current_app.logger.warning(f"Failed to get room details for reservation {reservation.id}")

        # Get attendees
        attendees = ReservationAttendee.query.filter_by(reservation_id=reservation.id).all()
        res_dict['attendees'] = [attendee.to_dict() for attendee in attendees]

        result.append(res_dict)

    return jsonify(result), 200


@reservation_bp.route('/<int:reservation_id>', methods=['GET'])
@auth_required
def get_reservation(reservation_id):
    """Get a specific reservation"""
    reservation = Reservation.query.get_or_404(reservation_id)

    # Check permissions (users can only view their own reservations unless admin)
    if g.user.get('id') != reservation.user_id and g.user.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    result = reservation.to_dict()

    # Get room details
    try:
        room_response = requests.get(
            f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{reservation.room_id}"
        )
        if room_response.status_code == 200:
            result['room'] = room_response.json()
    except requests.RequestException:
        current_app.logger.warning(f"Failed to get room details for reservation {reservation.id}")

    # Get attendees
    attendees = ReservationAttendee.query.filter_by(reservation_id=reservation.id).all()
    result['attendees'] = [attendee.to_dict() for attendee in attendees]

    return jsonify(result), 200


@reservation_bp.route('/check', methods=['GET'])
def check_availability():
    """Check if a room is available for a specific time period"""
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

    # Check for overlapping reservations
    overlapping = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        ((Reservation.start_time <= start_time) & (Reservation.end_time > start_time)) |
        ((Reservation.start_time < end_time) & (Reservation.end_time >= end_time)) |
        ((Reservation.start_time >= start_time) & (Reservation.end_time <= end_time))
    ).first()

    return jsonify({'available': not overlapping}), 200


@reservation_bp.route('/', methods=['POST'])
@auth_required
@employee_required
def create_reservation():
    """Create a new reservation"""
    data = request.get_json()

    # Validate required fields
    required_fields = ['room_id', 'start_time', 'end_time', 'title']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Missing required field: {field}"}), 400

    # Parse dates
    try:
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400

    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400

    # Check if room exists
    try:
        room_response = requests.get(
            f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{data['room_id']}"
        )
        if room_response.status_code != 200:
            return jsonify({'error': f"Room with ID {data['room_id']} not found"}), 404
    except requests.RequestException:
        current_app.logger.error(f"Failed to verify room {data['room_id']}")
        return jsonify({'error': "Room service unavailable"}), 503

    # Check room availability via room service
    try:
        availability_response = requests.get(
            f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{data['room_id']}/unavailability",
            params={
                'start_time': data['start_time'],
                'end_time': data['end_time']
            }
        )
        if availability_response.status_code == 200 and availability_response.json():
            return jsonify({'error': "Room is unavailable during the requested time"}), 409
    except requests.RequestException:
        current_app.logger.warning(f"Failed to check room availability for room {data['room_id']}")

    # Check for overlapping reservations
    overlapping = Reservation.query.filter(
        Reservation.room_id == data['room_id'],
        Reservation.status == ReservationStatus.CONFIRMED,
        ((Reservation.start_time <= start_time) & (Reservation.end_time > start_time)) |
        ((Reservation.start_time < end_time) & (Reservation.end_time >= end_time)) |
        ((Reservation.start_time >= start_time) & (Reservation.end_time <= end_time))
    ).first()

    if overlapping:
        return jsonify({'error': "Room is already reserved during the requested time"}), 409

    # Create the reservation
    reservation = Reservation(
        room_id=data['room_id'],
        user_id=g.user.get('id'),
        title=data['title'],
        description=data.get('description'),
        start_time=start_time,
        end_time=end_time,
        attendees_count=data.get('attendees_count', 1)
    )

    db.session.add(reservation)
    db.session.commit()

    # Add attendees if provided
    if 'attendees' in data and isinstance(data['attendees'], list):
        for attendee_data in data['attendees']:
            if isinstance(attendee_data, dict) and 'email' in attendee_data:
                attendee = ReservationAttendee(
                    reservation_id=reservation.id,
                    user_id=attendee_data.get('user_id'),
                    email=attendee_data['email'],
                    name=attendee_data.get('name')
                )
                db.session.add(attendee)
        db.session.commit()

    # Publish event to Kafka
    try:
        current_app.kafka_producer.produce(
            'reservation-events',
            key=str(reservation.id),
            value=json.dumps({
                'event': 'reservation_created',
                'reservation_id': reservation.id,
                'room_id': reservation.room_id,
                'user_id': reservation.user_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")

    # Retrieve attendees for the response
    attendees = ReservationAttendee.query.filter_by(reservation_id=reservation.id).all()
    result = reservation.to_dict()
    result['attendees'] = [attendee.to_dict() for attendee in attendees]

    return jsonify(result), 201


@reservation_bp.route('/<int:reservation_id>', methods=['PUT'])
@auth_required
def update_reservation(reservation_id):
    """Update a reservation"""
    reservation = Reservation.query.get_or_404(reservation_id)

    # Check permissions (users can only update their own reservations unless admin)
    if g.user.get('id') != reservation.user_id and g.user.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Check if reservation is active before allowing updates
    if not reservation.is_active:
        return jsonify({'error': f"Cannot update a reservation with status {reservation.status.value}"}), 400

    data = request.get_json()

    # Handle status changes separately
    if 'status' in data:
        try:
            new_status = ReservationStatus(data['status'])
            # Only allow changing status to "cancelled"
            if new_status != ReservationStatus.CANCELLED:
                return jsonify({'error': "Can only change status to 'cancelled'"}), 400

            reservation.status = new_status
            db.session.commit()

            # Publish cancellation event
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

            return jsonify(reservation.to_dict()), 200
        except ValueError:
            valid_statuses = [s.value for s in ReservationStatus]
            return jsonify({'error': f"Invalid status. Must be one of: {valid_statuses}"}), 400

    # For other updates, check for time conflicts
    start_time = reservation.start_time
    end_time = reservation.end_time
    room_id = reservation.room_id

    if 'start_time' in data:
        try:
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': "Invalid start_time format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400

    if 'end_time' in data:
        try:
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': "Invalid end_time format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400

    # Check if room is being changed and verify it exists
    if 'room_id' in data:
        room_id = data['room_id']
        try:
            room_response = requests.get(
                f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{room_id}"
            )
            if room_response.status_code != 200:
                return jsonify({'error': f"Room with ID {room_id} not found"}), 404
        except requests.RequestException:
            current_app.logger.error(f"Failed to verify room {room_id}")
            return jsonify({'error': "Room service unavailable"}), 503

    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400

    # Check for overlapping reservations (excluding the current reservation)
    overlapping = Reservation.query.filter(
        Reservation.id != reservation_id,
        Reservation.room_id == room_id,
        Reservation.status == ReservationStatus.CONFIRMED,
        ((Reservation.start_time <= start_time) & (Reservation.end_time > start_time)) |
        ((Reservation.start_time < end_time) & (Reservation.end_time >= end_time)) |
        ((Reservation.start_time >= start_time) & (Reservation.end_time <= end_time))
    ).first()

    if overlapping:
        return jsonify({'error': "Room is already reserved during the requested time"}), 409

    # Update fields
    if 'room_id' in data:
        reservation.room_id = data['room_id']
    if 'title' in data:
        reservation.title = data['title']
    if 'description' in data:
        reservation.description = data['description']
    if 'start_time' in data:
        reservation.start_time = start_time
    if 'end_time' in data:
        reservation.end_time = end_time
    if 'attendees_count' in data:
        reservation.attendees_count = data['attendees_count']

    # Update reservation attendees if provided
    if 'attendees' in data and isinstance(data['attendees'], list):
        ReservationAttendee.query.filter_by(reservation_id=reservation.id).delete()
        for attendee_data in data['attendees']:
            if isinstance(attendee_data, dict) and 'email' in attendee_data:
                attendee = ReservationAttendee(
                    reservation_id=reservation.id,
                    user_id=attendee_data.get('user_id'),
                    email=attendee_data['email'],
                    name=attendee_data.get('name')
                )
                db.session.add(attendee)

    db.session.commit()

    # Publish update event to Kafka
    try:
        current_app.kafka_producer.produce(
            'reservation-events',
            key=str(reservation.id),
            value=json.dumps({
                'event': 'reservation_updated',
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

    # Return updated reservation with attendees
    attendees = ReservationAttendee.query.filter_by(reservation_id=reservation.id).all()
    result = reservation.to_dict()
    result['attendees'] = [attendee.to_dict() for attendee in attendees]

    return jsonify(result), 200


@reservation_bp.route('/<int:reservation_id>', methods=['DELETE'])
@auth_required
def delete_reservation(reservation_id):
    """Delete (cancel) a reservation"""
    reservation = Reservation.query.get_or_404(reservation_id)

    # Check permissions (only own reservations or admin)
    if g.user.get('id') != reservation.user_id and g.user.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Instead of physical deletion, mark as cancelled
    reservation.status = ReservationStatus.CANCELLED
    db.session.commit()

    # Publish cancellation event
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

    return jsonify({'message': "Reservation cancelled successfully"}), 200


@reservation_bp.route('/stats', methods=['GET'])
@auth_required
@admin_required
def get_stats():
    """Get reservation statistics (admin only)"""
    # Total reservation count
    total_count = Reservation.query.count()

    # Count by status
    status_counts = {}
    for status in ReservationStatus:
        count = Reservation.query.filter(Reservation.status == status).count()
        status_counts[status.value] = count

    # Reservations in the last 30 days (assuming Reservation.created_at exists)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_count = Reservation.query.filter(Reservation.created_at >= thirty_days_ago).count()

    # Top rooms by reservation count
    room_stats = db.session.query(
        Reservation.room_id,
        db.func.count(Reservation.id).label('count')
    ).group_by(Reservation.room_id).order_by(db.desc('count')).limit(5).all()
    top_rooms = [{'room_id': room_id, 'count': count} for room_id, count in room_stats]

    # Top users by reservation count
    user_stats = db.session.query(
        Reservation.user_id,
        db.func.count(Reservation.id).label('count')
    ).group_by(Reservation.user_id).order_by(db.desc('count')).limit(5).all()
    top_users = [{'user_id': user_id, 'count': count} for user_id, count in user_stats]

    return jsonify({
        'total_count': total_count,
        'by_status': status_counts,
        'last_30_days': recent_count,
        'top_rooms': top_rooms,
        'top_users': top_users
    }), 200
