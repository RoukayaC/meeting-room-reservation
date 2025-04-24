from flask import Blueprint, request, jsonify, current_app, g
from .models import db, Room, RoomType, RoomUnavailability
import requests
from datetime import datetime, timedelta
import json
from functools import wraps

room_bp = Blueprint('room', __name__, url_prefix='/api/rooms')

def create_error_response(message, error_code):
    """Helper function to create standardized error responses"""
    return {
        "error": message,
        "code": error_code
    }

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
                return jsonify(create_error_response("Invalid token", "UNAUTHORIZED")), 401
                
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

@room_bp.route('/', methods=['GET'])
def get_rooms():
    """Get all rooms, with optional filtering"""
    # Get query parameters
    capacity = request.args.get('capacity', type=int)
    room_type = request.args.get('type')
    has_projector = request.args.get('has_projector', type=lambda v: v.lower() == 'true')
    has_video_conf = request.args.get('has_video_conf', type=lambda v: v.lower() == 'true')
    
    # Start with all rooms
    query = Room.query
    
    # Apply filters if provided
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    if room_type:
        try:
            room_type_enum = RoomType(room_type)
            query = query.filter(Room.room_type == room_type_enum)
        except ValueError:
            pass  # Invalid room type, ignore filter
    if has_projector is not None:
        query = query.filter(Room.has_projector == has_projector)
    if has_video_conf is not None:
        query = query.filter(Room.has_video_conf == has_video_conf)
    
    # Execute query
    rooms = query.all()
    return jsonify([room.to_dict() for room in rooms]), 200

@room_bp.route('/auth/validate', methods=['GET'])
def validate_token():
    """Proxy token validation via user service"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Missing or invalid Authorization header'}), 401

    try:
        response = requests.get(
            f"{current_app.config['USER_SERVICE_URL']}/api/auth/validate",
            headers={'Authorization': auth_header}
        )
        return jsonify(response.json()), response.status_code
    except requests.RequestException:
        current_app.logger.error("Failed to validate token via user service")
        return jsonify({'error': 'Token validation service unavailable'}), 503

@room_bp.route('/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Get a specific room"""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': "Room not found"}), 404
    return jsonify(room.to_dict()), 200

@room_bp.route('/', methods=['POST'])
@auth_required
@admin_required
def create_room():
    """Create a new room (admin only)"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'capacity', 'floor']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f"Missing required field: {field}"}), 400
    
    # Check if room name already exists
    if Room.query.filter_by(name=data['name']).first():
        return jsonify({'error': "Room with this name already exists"}), 409
    
    # Parse room type
    room_type = RoomType.MEETING  # Default
    if 'room_type' in data:
        try:
            room_type = RoomType(data['room_type'])
        except ValueError:
            return jsonify({'error': f"Invalid room type. Must be one of: {[r.value for r in RoomType]}"}), 400
    
    # Create room
    room = Room(
        name=data['name'],
        room_type=room_type,
        capacity=data['capacity'],
        floor=data['floor'],
        building=data.get('building'),
        has_projector=data.get('has_projector', False),
        has_video_conf=data.get('has_video_conf', False),
        has_whiteboard=data.get('has_whiteboard', True),
        description=data.get('description')
    )
    
    db.session.add(room)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'room-events',
            key=str(room.id),
            value=json.dumps({
                'event': 'room_created',
                'room_id': room.id,
                'name': room.name
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify(room.to_dict()), 201

@room_bp.route('/<int:room_id>', methods=['PUT'])
@auth_required
@admin_required
def update_room(room_id):
    """Update a room (admin only)"""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': "Room not found"}), 404
        
    data = request.get_json()
    
    # Update fields
    if 'name' in data and data['name'] != room.name:
        # Check if new name already exists
        if Room.query.filter_by(name=data['name']).first():
            return jsonify({'error': "Room with this name already exists"}), 409
        room.name = data['name']
    
    if 'room_type' in data:
        try:
            room.room_type = RoomType(data['room_type'])
        except ValueError:
            return jsonify({'error': f"Invalid room type. Must be one of: {[r.value for r in RoomType]}"}), 400
    
    if 'capacity' in data:
        room.capacity = data['capacity']
    if 'floor' in data:
        room.floor = data['floor']
    if 'building' in data:
        room.building = data['building']
    if 'has_projector' in data:
        room.has_projector = data['has_projector']
    if 'has_video_conf' in data:
        room.has_video_conf = data['has_video_conf']
    if 'has_whiteboard' in data:
        room.has_whiteboard = data['has_whiteboard']
    if 'description' in data:
        room.description = data['description']
    
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'room-events',
            key=str(room.id),
            value=json.dumps({
                'event': 'room_updated',
                'room_id': room.id,
                'name': room.name
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify(room.to_dict()), 200

@room_bp.route('/<int:room_id>', methods=['DELETE'])
@auth_required
@admin_required
def delete_room(room_id):
    """Delete a room (admin only)"""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': "Room not found"}), 404
    
    # Check if room has any unavailability records
    if RoomUnavailability.query.filter_by(room_id=room_id).first():
        # Delete associated unavailability records
        RoomUnavailability.query.filter_by(room_id=room_id).delete()
    
    db.session.delete(room)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'room-events',
            key=str(room_id),
            value=json.dumps({
                'event': 'room_deleted',
                'room_id': room_id
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify({'message': "Room deleted successfully"}), 200

@room_bp.route('/<int:room_id>/unavailability', methods=['POST'])
@auth_required
@admin_required
def add_unavailability(room_id):
    """Add a period when the room is unavailable (admin only)"""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': "Room not found"}), 404
        
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['start_time', 'end_time', 'reason']
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
    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400
    
    # Create unavailability record
    unavailability = RoomUnavailability(
        room_id=room_id,
        start_time=start_time,
        end_time=end_time,
        reason=data['reason']
    )
    
    db.session.add(unavailability)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'room-events',
            key=str(room_id),
            value=json.dumps({
                'event': 'room_unavailable',
                'room_id': room_id,
                'unavailability_id': unavailability.id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'reason': unavailability.reason
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify(unavailability.to_dict()), 201

@room_bp.route('/<int:room_id>/unavailability', methods=['GET'])
def get_unavailability(room_id):
    """Get all unavailability periods for a room"""
    room = db.session.get(Room, room_id)
    if not room:
        return jsonify({'error': "Room not found"}), 404
    
    # Get future unavailability periods
    now = datetime.utcnow()
    unavailability = RoomUnavailability.query.filter_by(room_id=room_id).filter(RoomUnavailability.end_time > now).all()
    
    return jsonify([u.to_dict() for u in unavailability]), 200

@room_bp.route('/unavailability/<int:unavailability_id>', methods=['DELETE'])
@auth_required
@admin_required
def delete_unavailability(unavailability_id):
    """Delete an unavailability period (admin only)"""
    unavailability = db.session.get(RoomUnavailability, unavailability_id)
    if not unavailability:
        return jsonify({'error': "Unavailability period not found"}), 404
        
    room_id = unavailability.room_id
    
    db.session.delete(unavailability)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'room-events',
            key=str(room_id),
            value=json.dumps({
                'event': 'room_unavailability_deleted',
                'room_id': room_id,
                'unavailability_id': unavailability_id
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify({'message': "Unavailability period deleted"}), 200

@room_bp.route('/availability', methods=['GET'])
def check_availability():
    """Check room availability for a specific time period"""
    # Get query parameters
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    capacity = request.args.get('capacity', type=int)
    
    if not start_time_str or not end_time_str:
        return jsonify({'error': "Both start_time and end_time are required"}), 400
    
    # Parse dates
    try:
        start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except ValueError:
        return jsonify({'error': "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)"}), 400
    
    # Validate dates
    if start_time >= end_time:
        return jsonify({'error': "Start time must be before end time"}), 400
    
    # Get all rooms that match capacity criteria
    query = Room.query
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    
    all_rooms = query.all()
    available_rooms = []
    
    # For each room, check if it's available during the requested time
    for room in all_rooms:
        # Check for unavailability periods
        unavailable = RoomUnavailability.query.filter_by(room_id=room.id).filter(
            ((RoomUnavailability.start_time <= start_time) & (RoomUnavailability.end_time > start_time)) |
            ((RoomUnavailability.start_time < end_time) & (RoomUnavailability.end_time >= end_time)) |
            ((RoomUnavailability.start_time >= start_time) & (RoomUnavailability.end_time <= end_time))
        ).first()
        
        if not unavailable:
            # Also check with reservation service
            reservation_service_url = current_app.config.get('RESERVATION_SERVICE_URL', 'http://reservation-service:5000')
            try:
                response = requests.get(
                    f"{reservation_service_url}/api/reservations/check",
                    params={
                        'room_id': room.id,
                        'start_time': start_time_str,
                        'end_time': end_time_str
                    }
                )
                
                if response.status_code == 200 and response.json().get('available', False):
                    available_rooms.append(room.to_dict())
            except requests.RequestException:
                # If reservation service is down, assume room is available
                current_app.logger.warning(f"Failed to check with reservation service for room {room.id}")
                available_rooms.append(room.to_dict())
    
    return jsonify(available_rooms), 200