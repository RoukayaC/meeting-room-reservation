from flask import Blueprint, request, jsonify, current_app, g
from .models import db, User, RoleEnum, Permission, RolePermission
import jwt
import datetime
from functools import wraps
import requests
from urllib.parse import urlencode
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def create_error_response(message, error_code):
    """Create a standardized error response"""
    return {
        "error": {
            "message": message,
            "code": error_code
        }
    }

def auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify(create_error_response("Authentication required", "UNAUTHORIZED")), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user = User.query.get(data['user_id'])
            if not g.user:
                return jsonify(create_error_response("User not found", "UNAUTHORIZED")), 401
                
            # Attach permissions to the user object
            g.user.permissions = get_user_permissions(g.user)
            
        except jwt.ExpiredSignatureError:
            return jsonify(create_error_response("Token expired", "UNAUTHORIZED")), 401
        except jwt.InvalidTokenError:
            return jsonify(create_error_response("Invalid token", "UNAUTHORIZED")), 401
            
        return f(*args, **kwargs)
    return decorated

def permission_required(permission_name):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user'):
                return jsonify(create_error_response("Authentication required", "UNAUTHORIZED")), 401
                
            if not has_permission(g.user, permission_name):
                return jsonify(create_error_response(f"Permission {permission_name} required", "FORBIDDEN")), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user'):
            return jsonify(create_error_response("Authentication required", "UNAUTHORIZED")), 401
        if g.user.role != RoleEnum.ADMIN:
            return jsonify(create_error_response("Admin privileges required", "FORBIDDEN")), 403
        return f(*args, **kwargs)
    return decorated

def employee_required(f):
    """Decorator to require employee role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user') or (not g.user.is_employee and not g.user.is_admin):
            return jsonify(create_error_response("Employee privileges required", "FORBIDDEN")), 403
        return f(*args, **kwargs)
    return decorated

def get_user_permissions(user):
    """Get all permissions for a user based on their role"""
    role_permissions = RolePermission.query.filter_by(role=user.role).all()
    return [rp.permission for rp in role_permissions]

def has_permission(user, permission_name):
    """Check if user has the specified permission"""
    # Admin has all permissions
    if user.is_admin:
        return True
        
    # Check user's permissions
    if hasattr(user, 'permissions'):
        return permission_name in [p.name for p in user.permissions]
    
    # Get permissions if not already attached
    permissions = get_user_permissions(user)
    return permission_name in [p.name for p in permissions]

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Login with email and password"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify(create_error_response("Email and password required", "BAD_REQUEST")), 400
        
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify(create_error_response("Invalid credentials", "UNAUTHORIZED")), 401
        
    # Get user permissions
    permissions = get_user_permissions(user)
    permission_names = [p.name for p in permissions]
    
    token = jwt.encode({
        'user_id': user.id,
        'role': user.role.value,
        'permissions': permission_names,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': user.to_dict(),
        'permissions': permission_names
    }), 200

@auth_bp.route('/google/auth', methods=['GET'])
def google_auth():
    """Start Google OAuth flow"""
    client_id = current_app.config['OAUTH_CLIENT_ID']
    redirect_uri = request.args.get('redirect_uri', '')
    
    if not client_id:
        return jsonify(create_error_response("OAuth not configured", "SERVER_ERROR")), 500
        
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    oauth_url = f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"
    return jsonify({'auth_url': oauth_url}), 200

@auth_bp.route('/validate', methods=['GET'])
def validate():
    """Validate token and return user info"""
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    if not token:
        return jsonify(create_error_response("Token required", "UNAUTHORIZED")), 401

    try:
        data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify(create_error_response("User not found", "NOT_FOUND")), 404
            
        # Get user permissions if not in token (for backward compatibility)
        permissions = data.get('permissions', [])
        if not permissions:
            permissions = [p.name for p in get_user_permissions(user)]
            
        user_dict = user.to_dict()
        user_dict['permissions'] = permissions
        
        return jsonify(user_dict), 200
    except jwt.ExpiredSignatureError:
        return jsonify(create_error_response("Token expired", "UNAUTHORIZED")), 401
    except jwt.InvalidTokenError:
        return jsonify(create_error_response("Invalid token", "UNAUTHORIZED")), 401

@auth_bp.route('/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback"""
    data = request.get_json()
    code = data.get('code')
    redirect_uri = data.get('redirect_uri')
    
    if not code:
        return jsonify(create_error_response("Authorization code required", "BAD_REQUEST")), 400
        
    # Exchange code for token
    try:
        token_response = requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': current_app.config['OAUTH_CLIENT_ID'],
                'client_secret': current_app.config['OAUTH_CLIENT_SECRET'],
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
        )
        token_data = token_response.json()
        
        if 'error' in token_data:
            return jsonify(create_error_response(token_data['error'], "BAD_REQUEST")), 400
            
        # Get user info
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f"Bearer {token_data['access_token']}"}
        )
        user_info = user_info_response.json()
        
        # Find or create user
        user = User.query.filter_by(email=user_info['email']).first()
        if not user:
            # Create new user
            user = User(
                email=user_info['email'],
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
                role=RoleEnum.EMPLOYEE,  # Default role
                oauth_provider='google',
                oauth_id=user_info['sub']
            )
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
        else:
            # Update OAuth info
            user.oauth_provider = 'google'
            user.oauth_id = user_info['sub']
            db.session.commit()
            
        # Get user permissions
        permissions = get_user_permissions(user)
        permission_names = [p.name for p in permissions]
        
        # Generate JWT
        token = jwt.encode({
            'user_id': user.id,
            'role': user.role.value,
            'permissions': permission_names,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': user.to_dict(),
            'permissions': permission_names
        }), 200
    except Exception as e:
        current_app.logger.error(f"OAuth error: {str(e)}")
        return jsonify(create_error_response("Authentication failed", "SERVER_ERROR")), 500

@auth_bp.route('/permissions', methods=['GET'])
@auth_required
def get_all_permissions():
    """Get all available permissions"""
    permissions = Permission.query.all()
    return jsonify([p.to_dict() for p in permissions]), 200

@auth_bp.route('/roles/permissions', methods=['GET'])
@auth_required
@admin_required
def get_role_permissions():
    """Get permissions for each role (admin only)"""
    roles = {role.value: [] for role in RoleEnum}
    
    role_permissions = RolePermission.query.all()
    for rp in role_permissions:
        roles[rp.role.value].append(rp.permission.to_dict())
    
    return jsonify(roles), 200

@auth_bp.route('/roles/permissions', methods=['POST'])
@auth_required
@admin_required
def update_role_permissions():
    """Update permissions for a role (admin only)"""
    data = request.get_json()
    
    if not data or 'role' not in data or 'permissions' not in data:
        return jsonify(create_error_response("Role and permissions required", "BAD_REQUEST")), 400
        
    try:
        role = RoleEnum(data['role'])
    except ValueError:
        return jsonify(create_error_response(f"Invalid role. Must be one of: {[r.value for r in RoleEnum]}", "BAD_REQUEST")), 400
        
    # Delete existing permissions for this role
    RolePermission.query.filter_by(role=role).delete()
    
    # Add new permissions
    for perm_name in data['permissions']:
        perm = Permission.query.filter_by(name=perm_name).first()
        if perm:
            role_perm = RolePermission(role=role, permission=perm)
            db.session.add(role_perm)
    
    db.session.commit()
    
    return jsonify({'message': f"Permissions updated for role {role.value}"}), 200