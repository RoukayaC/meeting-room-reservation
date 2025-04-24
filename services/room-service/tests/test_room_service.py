import unittest
from unittest.mock import patch, MagicMock
import json
import os
import sys
from datetime import datetime, timedelta

# Add the shared directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shared')))

from app import create_app
from app.models import db, Room, RoomType, RoomUnavailability

class RoomServiceTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and app context"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test_secret_key',
            'KAFKA_BOOTSTRAP_SERVERS': 'mock-kafka:9092',
            'SKIP_SAMPLE_DATA': True  
        })
        self.client = self.app.test_client()
        
        # Create app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create tables
        db.create_all()
        
        # Create test rooms
        meeting_room = Room(
            name="Test Meeting Room",
            room_type=RoomType.MEETING,
            capacity=8,
            floor="1st",
            building="Main Building",
            has_projector=True,
            has_video_conf=True,
            has_whiteboard=True
        )
        
        conference_room = Room(
            name="Test Conference Room",
            room_type=RoomType.CONFERENCE,
            capacity=20,
            floor="2nd",
            building="Main Building",
            has_projector=True,
            has_video_conf=True,
            has_whiteboard=True
        )
        
        db.session.add(meeting_room)
        db.session.add(conference_room)
        db.session.commit()
        
        # Mock admin auth
        self.patcher = patch('app.routes.requests')
        self.mock_requests = self.patcher.start()
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
    def test_get_rooms(self, mock_current_app):
        """Test getting all rooms"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request
        response = self.client.get('/api/rooms/')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)  
        self.assertEqual(data[0]['name'], 'Test Meeting Room')
        self.assertEqual(data[1]['name'], 'Test Conference Room')

    @patch('app.routes.current_app')
    def test_get_room_by_id(self, mock_current_app):
        """Test getting a specific room by ID"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request
        response = self.client.get('/api/rooms/1')
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'Test Meeting Room')
        self.assertEqual(data['room_type'], 'meeting')
        self.assertEqual(data['capacity'], 8)

    @patch('app.routes.current_app')
    def test_create_room(self, mock_current_app):
        """Test creating a new room"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Define new room data
        new_room = {
            'name': 'New Workshop Room',
            'room_type': 'workshop',
            'capacity': 30,
            'floor': '3rd',
            'building': 'Annex',
            'has_projector': False,
            'has_video_conf': False,
            'has_whiteboard': True,
            'description': 'A room for workshops'
        }
        
        # Make request with admin auth
        response = self.client.post(
            '/api/rooms/',
            data=json.dumps(new_room),
            content_type='application/json',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'New Workshop Room')
        self.assertEqual(data['room_type'], 'workshop')
        self.assertEqual(data['capacity'], 30)
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_update_room(self, mock_current_app):
        """Test updating a room"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Update data
        update_data = {
            'capacity': 10,
            'has_projector': False,
            'description': 'Updated description'
        }
        
        # Make request with admin auth
        response = self.client.put(
            '/api/rooms/1',
            data=json.dumps(update_data),
            content_type='application/json',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['capacity'], 10)
        self.assertEqual(data['has_projector'], False)
        self.assertEqual(data['description'], 'Updated description')
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_delete_room(self, mock_current_app):
        """Test deleting a room"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request with admin auth
        response = self.client.delete(
            '/api/rooms/1',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify room was deleted - using updated SQLAlchemy pattern
        self.assertIsNone(db.session.get(Room, 1))
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_add_unavailability(self, mock_current_app):
        """Test adding unavailability period to a room"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Unavailability data
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        unavailability_data = {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'reason': 'Maintenance'
        }
        
        # Make request with admin auth
        response = self.client.post(
            '/api/rooms/1/unavailability',
            data=json.dumps(unavailability_data),
            content_type='application/json',
            headers={'Authorization': 'Bearer fake-token'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['room_id'], 1)
        self.assertEqual(data['reason'], 'Maintenance')
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    @patch('app.routes.requests')
    def test_check_availability(self, mock_requests, mock_current_app):
        """Test checking room availability"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Mock reservation service response
        mock_requests.get.return_value.status_code = 200
        mock_requests.get.return_value.json.return_value = {'available': True}
        
        # Set up dates
        start_time = datetime.utcnow() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        
        # Make request
        response = self.client.get(
            f'/api/rooms/availability?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}&capacity=5'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)  

if __name__ == '__main__':
    unittest.main()