from flask import Blueprint, request, jsonify, current_app, g
from .models import db, Reservation, ReservationStatus, ReservationAttendee
import requests, json
from datetime import datetime
from functools import wraps

reservation_bp = Blueprint('reservation', __name__, url_prefix='/api/reservations')

# --- UTILITY DECORATORS ---
def require_roles(roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not token:
                return jsonify({'error': 'Authentication required'}), 401
            try:
                resp = requests.get(
                    f"{current_app.config['USER_SERVICE_URL']}/api/auth/validate",
                    headers={'Authorization': f'Bearer {token}'}
                )
                if resp.status_code != 200:
                    return jsonify({'error': 'Invalid token'}), 401
                g.user = resp.json()
                if roles and g.user.get('role') not in roles:
                    return jsonify({'error': f"{roles} access required"}), 403
            except requests.RequestException:
                return jsonify({'error': 'Auth service unavailable'}), 503
            return f(*args, **kwargs)
        return decorated
    return wrapper

auth_required = require_roles([])
admin_required = require_roles(['admin'])
employee_required = require_roles(['admin', 'employee'])

# --- UTILITY HELPERS ---
def parse_date_safe(date_str, end_of_day=False):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if end_of_day:
            return dt.replace(hour=23, minute=59, second=59)
        return dt
    except ValueError:
        return None

def fetch_attendees(res_id):
    return [a.to_dict() for a in ReservationAttendee.query.filter_by(reservation_id=res_id)]

def fetch_room(room_id):
    try:
        res = requests.get(f"{current_app.config['ROOM_SERVICE_URL']}/api/rooms/{room_id}")
        return res.json() if res.status_code == 200 else None
    except requests.RequestException:
        return None

# EXAMPLE CLEANED ROUTE
@reservation_bp.route('/<int:reservation_id>', methods=['GET'])
@auth_required
def get_reservation(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    if g.user['id'] != reservation.user_id and g.user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    res_dict = reservation.to_dict()
    res_dict['room'] = fetch_room(reservation.room_id)
    res_dict['attendees'] = fetch_attendees(reservation.id)

    return jsonify(res_dict), 200
