
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
import requests
import os

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = get_jwt_identity()
        
        # Call user service to check if user is admin
        user_service_url = os.environ.get('USER_SERVICE_URL', 'http://user-service:5000')
        try:
            headers = {'Authorization': request.headers.get('Authorization')}
            response = requests.get(f"{user_service_url}/api/users/profile", headers=headers)
            
            if response.status_code != 200:
                return jsonify({'error': 'Failed to authenticate user'}), 401
            
            user_data = response.json()
            if user_data.get('role') != 'admin':
                return jsonify({'error': 'Admin privileges required'}), 403
            
            return f(*args, **kwargs)
        except requests.RequestException as e:
            return jsonify({'error': f'Error authenticating user: {str(e)}'}), 500
    
    return decorated
