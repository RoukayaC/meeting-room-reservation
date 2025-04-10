import unittest
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

# Add the parent directory to the path so we can import the app package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Reservation

class ReservationServiceTestCase(unittest.TestCase):
    def setUp(self):
        # Configure the app for testing
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Mock JWT token verification for testing
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        
        self.client = self.app.test_client()
        
        # Create the database and tables
        with self.app.app_context():
            db.create_all()
            
            # Create test reservations
            now = datetime.utcnow()
            
            # Current reservation (happening now)
            reservation1 = Reservation(
                room_id=1,
                user_id=1,
                title='Team Meeting',
                description='Weekly team meeting',
                start_time=now - timedelta(hours=1),
                end_time=now + timedelta(hours=1),
                status='CONFIRMED'
            )
            
            # Future reservation
            reservation2 = Reservation(
                room_id=2,
                user_id=2,
                title='Project Planning',
                description='Planning session for new project',
                start_time=now + timedelta(days=1),
                end_time=now + timedelta(days=1, hours=2),
                status='CONFIRMED'
            )
            
            # Cancelled reservation
            reservation3 = Reservation(
                room_id=1,
                user_id=2,
                title='Client Meeting',
                description='Meeting with client',
                start_time=now + timedelta(days=2),
                end_time=now + timedelta(days=2, hours=1),
                status='CANCELLED'
            )
            
            db.session.add_all([reservation1, reservation2, reservation3])
            db.session.commit()
            
    def tearDown(self):
        # Clean up after each test
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_check(self):
        # Test the health check endpoint
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'reservation-service')
    
    @patch('app.routes.requests.get')
    def test_room_availability(self, mock_get):
        # Mock the room service response
        mock_get.return_value.status_code = 200
        
        # Test checking room availability for an available time
        now = datetime.utcnow()
        start = (now + timedelta(days=3)).isoformat()
        end = (now + timedelta(days=3, hours=2)).isoformat()
        
        # Room 1 should be available on day 3
        response = self.client.get(f'/rooms/1/availability?start_date={start}&end_date={end}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['available'])
    
    @patch('app.routes.requests.get')
    def test_room_not_available(self, mock_get):
        # Mock the room service response
        mock_get.return_value.status_code = 200
        
        # Test checking room availability for a time with existing reservation
        now = datetime.utcnow()
        
        # Room 2 has a reservation on day 1
        start = (now + timedelta(days=1)).isoformat()
        end = (now + timedelta(days=1, hours=1)).isoformat()
        
        response = self.client.get(f'/rooms/2/availability?start_date={start}&end_date={end}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['available'])
        self.assertTrue('conflicting_reservations' in data)
    
    def test_get_reservations(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test getting all reservations as admin
        response = self.client.get(
            '/reservations',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)  # All 3 reservations
    
    def test_get_reservations_as_user(self):
        # Mock JWT token for regular user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 2, 'email': 'user@example.com', 'role': 'EMPLOYEE'})
        
        # Test getting reservations as regular user (should only see own reservations)
        response = self.client.get(
            '/reservations',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)  # Only user 2's reservations
        
        # Verify all returned reservations belong to user 2
        for reservation in data:
            self.assertEqual(reservation['user_id'], 2)
    
    def test_cancel_reservation(self):
        # Mock JWT token for owner of reservation
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 2, 'email': 'user@example.com', 'role': 'EMPLOYEE'})
        
        # Test cancelling a future reservation (reservation 2)
        response = self.client.put(
            '/reservations/2/cancel',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'CANCELLED')
        
        # Verify the reservation was cancelled in the database
        with self.app.app_context():
            reservation = Reservation.query.get(2)
            self.assertEqual(reservation.status, 'CANCELLED')
    
    def test_create_reservation(self):
        # Mock JWT token for user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'user@example.com', 'role': 'EMPLOYEE'})
        
        now = datetime.utcnow()
        
        # Test creating a new reservation
        reservation_data = {
            'room_id': 3,
            'title': 'New Meeting',
            'description': 'Test reservation',
            'start_time': (now + timedelta(days=5)).isoformat(),
            'end_time': (now + timedelta(days=5, hours=1)).isoformat()
        }
        
        response = self.client.post(
            '/reservations',
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            data=json.dumps(reservation_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'New Meeting')
        self.assertEqual(data['room_id'], 3)
        self.assertEqual(data['user_id'], 1)
        self.assertEqual(data['status'], 'CONFIRMED')
        
        # Verify the reservation was added to the database
        with self.app.app_context():
            reservation = Reservation.query.filter_by(title='New Meeting').first()
            self.assertIsNotNone(reservation)
            self.assertEqual(reservation.room_id, 3)

if __name__ == '__main__':
    unittest.main()