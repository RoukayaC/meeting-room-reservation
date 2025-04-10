from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.models import Reservation
from app import db
from app.utils import (
    publish_message, RESERVATION_TOPIC, 
    role_required, ROOM_SERVICE_URL
)
from datetime import datetime
import requests

reservation_bp = Blueprint('reservation', __name__)

@reservation_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'reservation-service'})

@reservation_bp.route('/reservations', methods=['GET'])
@jwt_required()
def get_reservations():
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    role = current_user.get('role')
    
    # Get query parameters
    room_id = request.args.get('room_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Base query
    query = Reservation.query
    
    # Apply filters
    if room_id:
        query = query.filter(Reservation.room_id == room_id)
    
    if status:
        query = query.filter(Reservation.status == status.upper())
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(Reservation.start_time >= start_dt)
        except ValueError:
            return jsonify({'error': 'Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(Reservation.end_time <= end_dt)
        except ValueError:
            return jsonify({'error': 'Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    # Non-admin users can only see their own reservations
    if role != 'ADMIN':
        query = query.filter(Reservation.user_id == user_id)
    
    # Execute query
    reservations = query.all()
    
    return jsonify([reservation.to_dict() for reservation in reservations])

@reservation_bp.route('/reservations/<int:reservation_id>', methods=['GET'])
@jwt_required()
def get_reservation(reservation_id):
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    role = current_user.get('role')
    
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Check authorization
    if role != 'ADMIN' and reservation.user_id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    return jsonify(reservation.to_dict())

@reservation_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def check_room_availability(room_id):
    # Get query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({'error': 'Both start_date and end_date are required'}), 400
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    if start_dt >= end_dt:
        return jsonify({'error': 'start_date must be before end_date'}), 400
    
    # Check if room exists (optional, can be removed if too slow)
    try:
        response = requests.get(f"{ROOM_SERVICE_URL}/rooms/{room_id}")
        if response.status_code == 404:
            return jsonify({'error': 'Room not found'}), 404
    except requests.RequestException as e:
        logger.error(f"Failed to check room existence: {str(e)}")
        # Continue anyway, as the room might exist but the service is temporarily unavailable
    
    # Check for conflicting reservations
    conflicting_reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status == 'CONFIRMED',
        ~((Reservation.end_time <= start_dt) | (Reservation.start_time >= end_dt))
    ).all()
    
    if conflicting_reservations:
        conflicting_slots = [{
            'start_time': r.start_time.isoformat(),
            'end_time': r.end_time.isoformat(),
            'title': r.title
        } for r in conflicting_reservations]
        
        return jsonify({
            'available': False,
            'conflicting_reservations': conflicting_slots
        })
    
    return jsonify({'available': True})

@reservation_bp.route('/reservations', methods=['POST'])
@jwt_required()
def create_reservation():
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['room_id', 'title', 'start_time', 'end_time']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Field {field} is required'}), 400
    
    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'error': 'Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}), 400
    
    if start_time >= end_time:
        return jsonify({'error': 'start_time must be before end_time'}), 400
    
    if start_time < datetime.utcnow():
        return jsonify({'error': 'Cannot create reservations in the past'}), 400
    
    # Check room availability
    room_id = data['room_id']
    conflicting_reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.status == 'CONFIRMED',
        ~((Reservation.end_time <= start_time) | (Reservation.start_time >= end_time))
    ).all()
    
    if conflicting_reservations:
        return jsonify({
            'error': 'Room is not available for the selected time period',
            'conflicting_reservations': [
                {
                    'id': r.id,
                    'start_time': r.start_time.isoformat(),
                    'end_time': r.end_time.isoformat(),
                    'title': r.title
                } for r in conflicting_reservations
            ]
        }), 409
    
    # Create new reservation
    reservation = Reservation(
        room_id=room_id,
        user_id=user_id,
        title=data['title'],
        description=data.get('description', ''),
        start_time=start_time,
        end_time=end_time,
        status='CONFIRMED'
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    # Publish reservation created event
    publish_message(RESERVATION_TOPIC, 'RESERVATION_CREATED', reservation.to_dict())
    
    return jsonify(reservation.to_dict()), 201

@reservation_bp.route('/reservations/<int:reservation_id>', methods=['PUT'])
@jwt_required()
def update_reservation(reservation_id):
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    role = current_user.get('role')
    
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Check authorization - only the creator or admin can update
    if role != 'ADMIN' and reservation.user_id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Cannot update cancelled reservations
    if reservation.status == 'CANCELLED':
        return jsonify({'error': 'Cannot update cancelled reservations'}), 400
    
    data = request.get_json()
    
    # Handle time updates
    if 'start_time' in data or 'end_time' in data:
        start_time = datetime.fromisoformat(data.get('start_time', reservation.start_time.isoformat()))
        end_time = datetime.fromisoformat(data.get('end_time', reservation.end_time.isoformat()))
        
        if start_time >= end_time:
            return jsonify({'error': 'start_time must be before end_time'}), 400
        
        if start_time < datetime.utcnow():
            return jsonify({'error': 'Cannot update reservations to start in the past'}), 400
        
        # Check for conflicts only if time or room changes
        room_id = data.get('room_id', reservation.room_id)
        if (start_time != reservation.start_time or 
                end_time != reservation.end_time or 
                room_id != reservation.room_id):
            
            conflicting_reservations = Reservation.query.filter(
                Reservation.id != reservation_id,
                Reservation.room_id == room_id,
                Reservation.status == 'CONFIRMED',
                ~((Reservation.end_time <= start_time) | (Reservation.start_time >= end_time))
            ).all()
            
            if conflicting_reservations:
                return jsonify({
                    'error': 'Room is not available for the selected time period',
                    'conflicting_reservations': [
                        {
                            'id': r.id,
                            'start_time': r.start_time.isoformat(),
                            'end_time': r.end_time.isoformat(),
                            'title': r.title
                        } for r in conflicting_reservations
                    ]
                }), 409
        
        reservation.start_time = start_time
        reservation.end_time = end_time
    
    # Update other fields
    if 'room_id' in data:
        reservation.room_id = data['room_id']
    
    if 'title' in data:
        reservation.title = data['title']
    
    if 'description' in data:
        reservation.description = data['description']
    
    db.session.commit()
    
    # Publish reservation updated event
    publish_message(RESERVATION_TOPIC, 'RESERVATION_UPDATED', reservation.to_dict())
    
    return jsonify(reservation.to_dict())

@reservation_bp.route('/reservations/<int:reservation_id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_reservation(reservation_id):
    current_user = get_jwt_identity()
    user_id = current_user.get('id')
    role = current_user.get('role')
    
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Check authorization - only the creator or admin can cancel
    if role != 'ADMIN' and reservation.user_id != user_id:
        return jsonify({'error': 'Unauthorized access'}), 403
    
    # Cannot cancel already cancelled reservations
    if reservation.status == 'CANCELLED':
        return jsonify({'error': 'Reservation is already cancelled'}), 400
    
    # Cannot cancel past reservations
    if reservation.start_time < datetime.utcnow():
        return jsonify({'error': 'Cannot cancel past reservations'}), 400
    
    reservation.status = 'CANCELLED'
    db.session.commit()
    
    # Publish reservation cancelled event
    publish_message(RESERVATION_TOPIC, 'RESERVATION_CANCELLED', {
        'reservation_id': reservation.id,
        'cancelled_by': user_id
    })
    
    return jsonify(reservation.to_dict())

@reservation_bp.route('/admin/reservations/<int:reservation_id>', methods=['DELETE'])
@jwt_required()
@role_required('ADMIN')
def delete_reservation(reservation_id):
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return jsonify({'error': 'Reservation not found'}), 404
    
    # Physically delete the reservation (admin only)
    db.session.delete(reservation)
    db.session.commit()
    
    # Publish reservation deleted event
    publish_message(RESERVATION_TOPIC, 'RESERVATION_DELETED', {
        'reservation_id': reservation_id
    })
    
    return jsonify({'message': 'Reservation deleted successfully'})