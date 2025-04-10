from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import Room
from app import db
from app.utils import publish_message, ROOM_TOPIC

room_bp = Blueprint('room', __name__)

@room_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'room-service'})

@room_bp.route('/rooms', methods=['GET'])
def get_rooms():
    # Filter by active status if provided
    active_param = request.args.get('active')
    
    if active_param is not None:
        active = active_param.lower() == 'true'
        rooms = Room.query.filter_by(active=active).all()
    else:
        rooms = Room.query.all()
    
    return jsonify([room.to_dict() for room in rooms])

@room_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    return jsonify(room.to_dict())

@room_bp.route('/rooms', methods=['POST'])
@jwt_required()
def create_room():
    current_user = get_jwt_identity()
    
    # Only admins can create rooms
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'capacity', 'location']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Field {field} is required'}), 400
    
    # Check if room with same name already exists
    existing_room = Room.query.filter_by(name=data['name']).first()
    if existing_room:
        return jsonify({'error': 'Room with this name already exists'}), 409
    
    # Create new room
    room = Room(
        name=data['name'],
        capacity=data['capacity'],
        location=data['location'],
        equipment=data.get('equipment', ''),
        active=data.get('active', True)
    )
    
    db.session.add(room)
    db.session.commit()
    
    # Publish room created event
    publish_message(ROOM_TOPIC, 'ROOM_CREATED', room.to_dict())
    
    return jsonify(room.to_dict()), 201

@room_bp.route('/rooms/<int:room_id>', methods=['PUT'])
@jwt_required()
def update_room(room_id):
    current_user = get_jwt_identity()
    
    # Only admins can update rooms
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    data = request.get_json()
    
    # Update room properties
    if 'name' in data:
        existing_room = Room.query.filter_by(name=data['name']).first()
        if existing_room and existing_room.id != room_id:
            return jsonify({'error': 'Room with this name already exists'}), 409
        room.name = data['name']
    
    if 'capacity' in data:
        room.capacity = data['capacity']
    
    if 'location' in data:
        room.location = data['location']
    
    if 'equipment' in data:
        room.equipment = data['equipment']
    
    if 'active' in data:
        room.active = data['active']
    
    db.session.commit()
    
    # Publish room updated event
    publish_message(ROOM_TOPIC, 'ROOM_UPDATED', room.to_dict())
    
    return jsonify(room.to_dict())

@room_bp.route('/rooms/<int:room_id>/status', methods=['PUT'])
@jwt_required()
def update_room_status(room_id):
    current_user = get_jwt_identity()
    
    # Only admins can update room status
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    data = request.get_json()
    if 'active' not in data:
        return jsonify({'error': 'Active status is required'}), 400
    
    room.active = data['active']
    db.session.commit()
    
    # Publish room status updated event
    publish_message(ROOM_TOPIC, 'ROOM_STATUS_UPDATED', {
        'room_id': room.id,
        'active': room.active
    })
    
    return jsonify(room.to_dict())

@room_bp.route('/rooms/<int:room_id>', methods=['DELETE'])
@jwt_required()
def delete_room(room_id):
    current_user = get_jwt_identity()
    
    # Only admins can delete rooms
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    room = Room.query.get(room_id)
    if not room:
        return jsonify({'error': 'Room not found'}), 404
    
    # Soft delete - just mark as inactive
    room.active = False
    db.session.commit()
    
    # Publish room deleted event
    publish_message(ROOM_TOPIC, 'ROOM_DELETED', {'room_id': room.id})
    
    return jsonify({'message': 'Room deleted successfully'})