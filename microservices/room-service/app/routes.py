
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Room
from app import db
from app.utils import admin_required

room_bp = Blueprint('room', __name__, url_prefix='/api/rooms')

# Get all rooms
@room_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_rooms():
    # Get query parameters
    capacity = request.args.get('capacity', type=int)
    location = request.args.get('location')
    
    # Base query
    query = Room.query.filter_by(is_active=True)
    
    # Apply filters if provided
    if capacity:
        query = query.filter(Room.capacity >= capacity)
    if location:
        query = query.filter(Room.location.ilike(f'%{location}%'))
    
    rooms = query.all()
    return jsonify([room.to_dict() for room in rooms]), 200
