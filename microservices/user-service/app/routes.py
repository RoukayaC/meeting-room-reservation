from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from app.models import User
from app import db, oauth
from app.utils import publish_message, USER_TOPIC
from datetime import timedelta

user_bp = Blueprint('user', __name__)

@user_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'user-service'})

@user_bp.route('/login/google')
def login_google():
    redirect_uri = url_for('user.authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@user_bp.route('/authorize')
def authorize():
    token = oauth.google.authorize_access_token()
    resp = oauth.google.get('userinfo')
    user_info = resp.json()
    
    # Check if user exists
    user = User.query.filter_by(email=user_info['email']).first()
    
    if not user:
        # Create new user with default role EMPLOYEE
        user = User(
            email=user_info['email'],
            name=user_info['name'],
            role='EMPLOYEE'
        )
        db.session.add(user)
        db.session.commit()
        
        # Publish user created event
        publish_message(USER_TOPIC, 'USER_CREATED', user.to_dict())
    
    # Create JWT token
    access_token = create_access_token(
        identity={
            'id': user.id,
            'email': user.email,
            'role': user.role
        },
        expires_delta=timedelta(hours=1)
    )
    
    return jsonify(access_token=access_token, user=user.to_dict())

@user_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    current_user = get_jwt_identity()
    
    # Check if user has admin role
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user = get_jwt_identity()
    
    # Users can access their own data, admins can access all
    if current_user['id'] != user_id and current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@jwt_required()
def update_user_role(user_id):
    current_user = get_jwt_identity()
    
    # Only admins can change roles
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    data = request.get_json()
    if 'role' not in data:
        return jsonify({'error': 'Role is required'}), 400
    
    # Validate role
    valid_roles = ['ADMIN', 'EMPLOYEE', 'VISITOR']
    if data['role'] not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of {valid_roles}'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    old_role = user.role
    user.role = data['role']
    db.session.commit()
    
    # Publish role updated event
    publish_message(USER_TOPIC, 'USER_ROLE_UPDATED', {
        'user_id': user.id,
        'old_role': old_role,
        'new_role': user.role
    })
    
    return jsonify(user.to_dict())

@user_bp.route('/users/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def update_user_status(user_id):
    current_user = get_jwt_identity()
    
    # Only admins can change status
    if current_user['role'] != 'ADMIN':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    data = request.get_json()
    if 'active' not in data:
        return jsonify({'error': 'Active status is required'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    user.active = data['active']
    db.session.commit()
    
    # Publish status updated event
    publish_message(USER_TOPIC, 'USER_STATUS_UPDATED', {
        'user_id': user.id,
        'active': user.active
    })
    
    return jsonify(user.to_dict())

@user_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict())