from flask import Blueprint, request, jsonify, current_app, g
from .models import db, User, RoleEnum
from .auth import auth_required, admin_required, create_error_response, permission_required
import json

user_bp = Blueprint('user', __name__, url_prefix='/api/users')

@user_bp.route('/', methods=['GET'])
@auth_required
@admin_required
def get_users():
    """Get all users (admin only)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@user_bp.route('/<int:user_id>', methods=['GET'])
@auth_required
def get_user(user_id):
    """Get a specific user"""
    # Check permissions (users can only see their own info unless admin)
    if g.user.id != user_id and not g.user.is_admin:
        return jsonify(create_error_response("Unauthorized access", "FORBIDDEN")), 403
        
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200

@user_bp.route('/', methods=['POST'])
@auth_required
@admin_required
def create_user():
    """Create a new user (admin only)"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'first_name', 'last_name', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify(create_error_response(f"Missing required field: {field}", "BAD_REQUEST")), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify(create_error_response("Email already registered", "CONFLICT")), 409
    
    # Create user
    try:
        role = RoleEnum(data['role'])
    except ValueError:
        return jsonify(create_error_response(f"Invalid role. Must be one of: {[r.value for r in RoleEnum]}", "BAD_REQUEST")), 400
    
    user = User(
        email=data['email'],
        first_name=data['first_name'],
        last_name=data['last_name'],
        role=role,
        department=data.get('department')
    )
    
    # Set password if provided
    if 'password' in data:
        user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'user-events',
            key=str(user.id),
            value=json.dumps({
                'event': 'user_created',
                'user_id': user.id,
                'email': user.email,
                'role': user.role.value
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify(user.to_dict()), 201

@user_bp.route('/<int:user_id>', methods=['PUT'])
@auth_required
def update_user(user_id):
    """Update a user"""
    # Check permissions (users can only update their own info unless admin)
    if g.user.id != user_id and not g.user.is_admin:
        return jsonify(create_error_response("Unauthorized access", "FORBIDDEN")), 403
        
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    # Update fields
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'department' in data:
        user.department = data['department']
    
    # Only admin can update role
    if 'role' in data and g.user.is_admin:
        try:
            user.role = RoleEnum(data['role'])
        except ValueError:
            return jsonify(create_error_response(f"Invalid role. Must be one of: {[r.value for r in RoleEnum]}", "BAD_REQUEST")), 400
    
    # Update password
    if 'password' in data:
        user.set_password(data['password'])
    
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'user-events',
            key=str(user.id),
            value=json.dumps({
                'event': 'user_updated',
                'user_id': user.id,
                'email': user.email,
                'role': user.role.value
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify(user.to_dict()), 200

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@auth_required
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting the last admin
    if user.role == RoleEnum.ADMIN:
        admin_count = User.query.filter_by(role=RoleEnum.ADMIN).count()
        if admin_count <= 1:
            return jsonify(create_error_response("Cannot delete the last admin user", "BAD_REQUEST")), 400
    
    db.session.delete(user)
    db.session.commit()
    
    # Publish to Kafka
    try:
        current_app.kafka_producer.produce(
            'user-events',
            key=str(user_id),
            value=json.dumps({
                'event': 'user_deleted',
                'user_id': user_id
            })
        )
        current_app.kafka_producer.flush()
    except Exception as e:
        current_app.logger.error(f"Failed to publish to Kafka: {str(e)}")
    
    return jsonify({'message': "User deleted successfully"}), 200