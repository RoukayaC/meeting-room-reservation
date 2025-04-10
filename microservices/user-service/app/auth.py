from flask import Blueprint, request, jsonify, current_app, g
from .models import db, User, RoleEnum
import jwt
import datetime
from functools import wraps
import requests
from urllib.parse import urlencode
import json

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

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
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user = User.query.get(data['user_id'])
            if not g.user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user') or not g.user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated

def employee_required(f):
    """Decorator to require employee role"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user') or (not g.user.is_employee and not g.user.is_admin):
            return jsonify({'error': 'Employee privileges required'}), 403
        return f(*args, **kwargs)
    return decorated

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login with email and password"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
        
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
        
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')
    
    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/google/auth', methods=['GET'])
def google_auth():
    """Start Google OAuth flow"""
    client_id = current_app.config['OAUTH_CLIENT_ID']
    redirect_uri = request.args.get('redirect_uri', '')
    
    if not client_id:
        return jsonify({'error': 'OAuth not configured'}), 500
        
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

@auth_bp.route('/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback"""
    data = request.get_json()
    code = data.get('code')
    redirect_uri = data.get('redirect_uri')
    
    if not code:
        return jsonify({'error': 'Authorization code required'}), 400
        
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
            return jsonify({'error': token_data['error']}), 400
            
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
            
        # Generate JWT
        token = jwt.encode({
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({
            'token': token,
            'user': user.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"OAuth error: {str(e)}")
        return jsonify({'error': 'Authentication failed'}), 500