
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Reservation
from app import db
from datetime import datetime
from app.utils import get_user_data, get_room_data

reservation_bp = Blueprint('reservation', __name__, url_prefix='/api/reservations')

# Get all reservations for a user
@reservation_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user_reservations():
    user_id = get_jwt_identity()
    
    # Get query parameters
    status = request.args.get('status')
    
    # Base query
    query = Reservation.query.filter_by(user_id=user_id)
    
    # Apply filters if provided
    if status:
        query = query.filter_by(status=status)
    
    # Order by start time
    query = query.order_by(Reservation.start_time)
    
    reservations = query.all()
    
    # Fetch room details for each reservation
    result = []
    for reservation in reservations:
        res_dict = reservation.to_dict()
        room_data = get_room_data(reservation.room_id)
        if room_data:
            res_dict['room'] = room_data
        result.append(res_dict)
    
    return jsonify(result), 200
