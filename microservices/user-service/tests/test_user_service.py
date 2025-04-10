import unittest
import json
import os
import sys
from datetime import datetime

# Add the parent directory to the path so we can import the app package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User

class UserServiceTestCase(unittest.TestCase):
    def setUp(self):
        # Configure the app for testing
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        # Create the database and tables
        with self.app.app_context():
            db.create_all()
            
            # Create test admin user
            admin = User(
                email='admin@example.com',
                name='Admin User',
                role='ADMIN',
                active=True
            )
            
            # Create test employee user
            employee = User(
                email='employee@example.com',
                name='Employee User',
                role='EMPLOYEE',
                active=True
            )
            
            # Create test visitor user
            visitor = User(
                email='visitor@example.com',
                name='Visitor User',
                role='VISITOR',
                active=True
            )
            
            db.session.add_all([admin, employee, visitor])
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
        self.assertEqual(data['service'], 'user-service')
    
    def test_get_users_unauthorized(self):
        # Test that unauthenticated users cannot access the users list
        response = self.client.get('/users')
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_get_user_by_id(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test getting a specific user with admin token
        response = self.client.get('/users/2', headers={'Authorization': f'Bearer {access_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['email'], 'employee@example.com')
        self.assertEqual(data['role'], 'EMPLOYEE')
    
    def test_get_users_as_admin(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test getting all users with admin token
        response = self.client.get('/users', headers={'Authorization': f'Bearer {access_token}'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 3)  # Should get all 3 test users
    
    def test_update_user_role(self):
        # Mock JWT token for admin user
        with self.app.test_request_context():
            from flask_jwt_extended import create_access_token
            access_token = create_access_token(identity={'id': 1, 'email': 'admin@example.com', 'role': 'ADMIN'})
        
        # Test updating a user's role
        response = self.client.put(
            '/users/3/role', 
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            data=json.dumps({'role': 'EMPLOYEE'})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['role'], 'EMPLOYEE')
        
        # Verify the role was updated in the database
        with self.app.app_context():
            user = User.query.get(3)
            self.assertEqual(user.role, 'EMPLOYEE')

if __name__ == '__main__':
    unittest.main()