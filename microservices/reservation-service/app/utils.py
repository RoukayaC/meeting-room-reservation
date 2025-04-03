
import requests
import os
from flask import request

def get_user_data(user_id):
    """Get user data from the user service"""
    user_service_url = os.environ.get('USER_SERVICE_URL', 'http://user-service:5000')
    try:
        headers = {'Authorization': request.headers.get('Authorization')}
        response = requests.get(f"{user_service_url}/api/users/{user_id}", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def get_room_data(room_id):
    """Get room data from the room service"""
    room_service_url = os.environ.get('ROOM_SERVICE_URL', 'http://room-service:5000')
    try:
        headers = {'Authorization': request.headers.get('Authorization')}
        response = requests.get(f"{room_service_url}/api/rooms/{room_id}", headers=headers)
        
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None
