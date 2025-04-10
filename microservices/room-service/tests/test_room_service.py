import unittest
import json
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import the app package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import Room

class RoomServiceTestCase(unittest.TestCase):
    def setUp(self):
        # Configure the app for testing
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        # Create the database and tables
        with self.app.app_context():
            db.create_all()
            
            # Create test rooms
            room1 = Room(
                name='Conference Room A',
                capacity=10,
                location='1st Floor',
                equipment='Projector, Whiteboard',
                active=True
            )
            
            room2 = Room(
                name='Conference Room B',
                capacity=6,
                location='2nd Floor',
                equipment='TV, Whiteboard',
                active=True
            )
            
            room3 = Room(
                name='Meeting Room C',
                capacity=4,
                location='3rd Floor',
                equipment='Whiteboard',
                active=False  # Inactive room
            )
            
            db.session.add_all([room1, room2, room3])
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
        self.assertEqual(data['service'], 'room-service')
    
    def test_get_rooms(self):
        # Test getting all rooms
        response = self.client.get('/rooms')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)  # All 3 rooms returned
    
    def test_get_active_rooms(self):
        # Test filtering active rooms
        response = self.client.get('/rooms?active=true')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)  # Only 2 active rooms returned
    
    def test_get_room_by_id(self):
        # Test getting a specific room
        response = self.client.get('/rooms/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'Conference Room A')
        self.assertEqual(data['capacity'], 10)
        self.assertEqual(data['location'], '1st Floor')
    
    def test_create_room(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test creating a new room
        room_data = {
            'name': 'New Room',
            'capacity': 8,
            'location': '4th Floor',
            'equipment': 'Projector, Whiteboard, TV'
        }
        
        response = self.client.post(
            '/rooms',
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            data=json.dumps(room_data)
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], 'New Room')
        
        # Verify the room was added to the database
        with self.app.app_context():
            room = Room.query.filter_by(name='New Room').first()
            self.assertIsNotNone(room)
            self.assertEqual(room.capacity, 8)

    def test_update_room(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test updating a room
        update_data = {
            'capacity': 12,
            'equipment': 'Updated Equipment'
        }
        
        response = self.client.put(
            '/rooms/1',
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            data=json.dumps(update_data)
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['capacity'], 12)
        self.assertEqual(data['equipment'], 'Updated Equipment')
        
        # Verify the room was updated in the database
        with self.app.app_context():
            room = Room.query.get(1)
            self.assertEqual(room.capacity, 12)
            self.assertEqual(room.equipment, 'Updated Equipment')

if __name__ == '__main__':
    unittest.main()