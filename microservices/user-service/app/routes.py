
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from app.models import User, OAuth
from app import db
import requests
import os
from datetime import timedelta

user_bp = Blueprint('user', __name__, url_prefix='/api/users')

# User registration
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Check if required fields are present
    required_fields = ['email', 'password', 'first_name', 'last_name']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'User already exists'}), 409
    
    # Create new user
    user = User(
        email=data['email'],
        password=data['password'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=data.get('role', 'employee')
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Create and return tokens
    access_token = create_access_token(identity=user.id, expires_delta=timedelta(hours=1))
    refresh_token = create_refresh_token(identity=user.id, expires_delta=timedelta(days=30))
    
    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201

# User login
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Check if required fields are present
    if 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Missing email or password'}), 400
    
    # Check if user exists and password is correct
    user = User.query.filter_by(email=data['email']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Create and return tokens
    access_token = create_access_token(identity=user.id, expires_delta=timedelta(hours=1))
    refresh_token = create_refresh_token(identity=user.id, expires_delta=timedelta(days=30))
    
    return jsonify({
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200

# Get user profile
@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def profile():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200
