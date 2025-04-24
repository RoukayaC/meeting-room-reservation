import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os
from datetime import datetime, timedelta

# Add the shared directory to the Python path if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shared')))

from app import create_app
from app.models import db, Reservation, ReservationStatus, ReservationAttendee

class ReservationServiceTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and app context"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test_secret_key',
            'KAFKA_BOOTSTRAP_SERVERS': 'mock-kafka:9092'
        })
        self.client = self.app.test_client()
        
        # Create app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create tables
        db.create_all()
        
        # Create test reservations
        future_reservation = Reservation(
            room_id=1,
            user_id=1,
            title="Test Meeting",
            description="A test meeting",
            start_time=datetime.utcnow() + timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=1, hours=1),
            status=ReservationStatus.CONFIRMED,
            attendees_count=3
        )
        
        past_reservation = Reservation(
            room_id=2,
            user_id=1,
            title="Past Meeting",
            description="A past meeting",
            start_time=datetime.utcnow() - timedelta(days=1, hours=2),
            end_time=datetime.utcnow() - timedelta(days=1, hours=1),
            status=ReservationStatus.COMPLETED,
            attendees_count=2
        )
        
        db.session.add(future_reservation)
        db.session.add(past_reservation)
        db.session.commit()
        
        # Add attendees to future reservation
        attendee1 = ReservationAttendee(
            reservation_id=1,
            user_id=1,
            email="admin@test.com",
            name="Admin User"
        )
        
        attendee2 = ReservationAttendee(
            reservation_id=1,
            user_id=2,
            email="employee@test.com",
            name="Test Employee"
        )
        
        db.session.add(attendee1)
        db.session.add(attendee2)
        db.session.commit()
        
        # Mock auth
        self.patcher = patch('app.routes.requests')
        self.mock_requests = self.patcher.start()
        
        # Mock admin auth by default
        self.mock_requests.get.return_value.status_code = 200
        self.mock_requests.get.return_value.json.return_value = {
            'id': 1,
            'email': 'admin@test.com',
            'role': 'admin'
        }

    def tearDown(self):
        """Clean up after each test"""
        self.patcher.stop()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('app.routes.current_app')
    @patch('app.routes.fetch_room')
    def test_get_reservation(self, mock_fetch_room, mock_current_app):
        """Test getting a reservation by ID"""
        # Mock Kafka producer and room details
        mock_current_app.kafka_producer = MagicMock()
        mock_fetch_room.return_value = {
            'id': 1,
            'name': 'Test Meeting Room',
            'capacity': 8
        }
        
        # Make request with auth
        response = self.client.get(
            '/api/reservations/1',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Test Meeting')
        self.assertEqual(data['room_id'], 1)
        self.assertEqual(data['status'], 'confirmed')
        self.assertEqual(len(data['attendees']), 2)

    @patch('app.routes.current_app')
    def test_create_reservation(self, mock_current_app):
        """Test creating a new reservation"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Set up start and end times
        start_time = datetime.utcnow() + timedelta(days=2)
        end_time = start_time + timedelta(hours=1)
        
        # Define new reservation data
        new_reservation = {
            'room_id': 1,
            'title': 'New Meeting',
            'description': 'A new test meeting',
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'attendees': [
                {'email': 'admin@test.com', 'name': 'Admin User'},
                {'email': 'guest@test.com', 'name': 'Guest User'}
            ]
        }
        
        # Mock room availability check
        self.mock_requests.get.side_effect = lambda url, **kwargs: MagicMock(
            status_code=200,
            json=lambda: {'available': True}
        ) if 'check' in url else self.mock_requests.get.return_value
        
        # Make request with auth
        response = self.client.post(
            '/api/reservations/',
            data=json.dumps(new_reservation),
            content_type='application/json',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'New Meeting')
        self.assertEqual(data['room_id'], 1)
        self.assertEqual(data['status'], 'confirmed')
        self.assertEqual(data['attendees_count'], 2)
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_update_reservation(self, mock_current_app):
        """Test updating a reservation"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Update data
        update_data = {
            'title': 'Updated Meeting',
            'description': 'An updated meeting description'
        }
        
        # Make request with auth
        response = self.client.put(
            '/api/reservations/1',
            data=json.dumps(update_data),
            content_type='application/json',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['title'], 'Updated Meeting')
        self.assertEqual(data['description'], 'An updated meeting description')
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_cancel_reservation(self, mock_current_app):
        """Test cancelling a reservation"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request with auth
        response = self.client.delete(
            '/api/reservations/1',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify reservation was cancelled (not deleted)
        reservation = db.session.get(Reservation, 1)
        self.assertEqual(reservation.status, ReservationStatus.CANCELLED)
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_list_user_reservations(self, mock_current_app):
        """Test listing reservations for a user"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request with auth
        response = self.client.get(
            '/api/reservations/user/1',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)  

if __name__ == '__main__':
    unittest.main()