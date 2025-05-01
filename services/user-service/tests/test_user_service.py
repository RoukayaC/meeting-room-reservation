import unittest
from unittest.mock import patch, MagicMock, call
import json
import jwt
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, RoleEnum, Permission, RolePermission

class UserServiceTestCase(unittest.TestCase):
    def setUp(self):
        """Set up test client and app context"""
        self.app = create_app({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'test_secret_key',
            'KAFKA_BOOTSTRAP_SERVERS': 'mock-kafka:9092',
            'ADMIN_EMAIL': 'admin@test.com', 
            'ADMIN_PASSWORD': 'adminpassword'
        })
        self.client = self.app.test_client()
        
        # Create app context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create tables
        db.create_all()
        
        # Create test admin user
        admin = User(
            email='admin@test.com',
            first_name='Admin',
            last_name='User',
            role=RoleEnum.ADMIN
        )
        admin.set_password('password123')
        db.session.add(admin)
        
        # Create test employee user
        employee = User(
            email='roukaya@gmail.com',
            first_name='Roukaya',
            last_name='Chelly',
            role=RoleEnum.EMPLOYEE
        )
        employee.set_password('roukaya')
        db.session.add(employee)
        
        db.session.commit()
        
        # Get the user IDs after commit
        self.admin = User.query.filter_by(email='admin@test.com').first()
        self.admin_id = self.admin.id
        
        self.employee = User.query.filter_by(email='roukaya@gmail.com').first()
        self.employee_id = self.employee.id
        
        print(f"Setup: admin_id={self.admin_id}, employee_id={self.employee_id}")
        
        # Add permissions (similar to what create_app does) - with idempotent handling
        permissions = [
            Permission(name='user:read', description='View user details'),
            Permission(name='user:create', description='Create new users'),
            Permission(name='user:update', description='Update user details'),
            Permission(name='user:delete', description='Delete users'),
            Permission(name='user:list', description='List all users')
        ]
        
        for permission in permissions:
            existing = Permission.query.filter_by(name=permission.name).first()
            if not existing:
                db.session.add(permission)
        
        db.session.commit()
        
        # Assign permissions to roles - with idempotent handling
        admin_permissions = Permission.query.all()
        for permission in admin_permissions:
            exists = RolePermission.query.filter_by(role=RoleEnum.ADMIN, permission_id=permission.id).first()
            if not exists:
                role_permission = RolePermission(role=RoleEnum.ADMIN, permission=permission)
                db.session.add(role_permission)
        
        # Employee permissions - just user:read - with idempotent handling
        employee_permission = Permission.query.filter_by(name='user:read').first()
        if employee_permission:
            exists = RolePermission.query.filter_by(role=RoleEnum.EMPLOYEE, permission_id=employee_permission.id).first()
            if not exists:
                role_permission = RolePermission(role=RoleEnum.EMPLOYEE, permission=employee_permission)
                db.session.add(role_permission)
                
        db.session.commit()
        
        # Create test tokens with proper permissions
        admin_perms = [p.name for p in Permission.query.all()]
        employee_perms = ['user:read']
        
        self.admin_token = jwt.encode({
            'user_id': self.admin_id,
            'role': 'admin',
            'permissions': admin_perms,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, self.app.config['SECRET_KEY'], algorithm='HS256')
        
        self.employee_token = jwt.encode({
            'user_id': self.employee_id,
            'role': 'employee',
            'permissions': employee_perms,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, self.app.config['SECRET_KEY'], algorithm='HS256')

    def tearDown(self):
        """Clean up after each test"""
        # Ensure we properly clean up to avoid test contamination
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch('app.routes.current_app')
    def test_get_users_as_admin(self, mock_current_app):
        """Test getting all users as admin"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()

        # Make request as admin
        response = self.client.get(
            '/api/users/',
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreaterEqual(len(data), 2)  # At least 2 users (admin and employee)

    @patch('app.routes.current_app')
    def test_get_users_as_employee(self, mock_current_app):
        """Test getting all users as employee (should be forbidden)"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request as employee
        response = self.client.get(
            '/api/users/',
            headers={'Authorization': f'Bearer {self.employee_token}'}
        )
        
        # Check response (should be forbidden)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('app.routes.current_app')
    def test_create_user(self, mock_current_app):
        """Test creating a new user as admin"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Define new user data
        new_user = {
            'email': 'roukaya2@gmail.com',
            'first_name': 'roukaya2',
            'last_name': 'chelly2',
            'role': 'employee',
            'password': 'roukaya',
            'department': 'Engineering'
        }
        
        # Make request as admin
        response = self.client.post(
            '/api/users/',
            data=json.dumps(new_user),
            content_type='application/json',
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 201, f"Response body: {response.data}")
        data = json.loads(response.data)
        self.assertEqual(data['email'], 'roukaya2@gmail.com')
        self.assertEqual(data['role'], 'employee')
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        mock_current_app.kafka_producer.flush.assert_called_once()

    @patch('app.routes.current_app')
    def test_create_user_duplicate_email(self, mock_current_app):
        """Test creating a user with duplicate email"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Define user data with existing email
        duplicate_user = {
            'email': 'admin@test.com',  # Email already exists
            'first_name': 'Another',
            'last_name': 'Admin',
            'role': 'admin',
            'password': 'password123'
        }
        
        # Make request as admin
        response = self.client.post(
            '/api/users/',
            data=json.dumps(duplicate_user),
            content_type='application/json',
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response - should be conflict
        self.assertEqual(response.status_code, 409)
        
        # Verify Kafka message was NOT sent
        mock_current_app.kafka_producer.produce.assert_not_called()

    @patch('app.routes.current_app')
    def test_update_user(self, mock_current_app):
        """Test updating a user"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Update data
        update_data = {
            'first_name': 'Updated',
            'department': 'HR'
        }
        
        # Make request as admin
        response = self.client.put(
            f'/api/users/{self.employee_id}',  # Update employee user
            data=json.dumps(update_data),
            content_type='application/json',
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['first_name'], 'Updated')
        self.assertEqual(data['department'], 'HR')
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        # Get the actual call arguments
        call_args = mock_current_app.kafka_producer.produce.call_args
        self.assertEqual(call_args[0][0], 'user-events')  # Check topic
        self.assertEqual(call_args[1]['key'], str(self.employee_id))  # Check key
        
        # Parse and check the message content
        message_content = json.loads(call_args[1]['value'])
        self.assertEqual(message_content['event'], 'user_updated')
        self.assertEqual(message_content['user_id'], self.employee_id)
        self.assertEqual(message_content['email'], 'roukaya@gmail.com')
        self.assertEqual(message_content['role'], 'employee')

    @patch('app.routes.current_app')
    def test_delete_user(self, mock_current_app):
        """Test deleting a user"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make request as admin
        response = self.client.delete(
            f'/api/users/{self.employee_id}',  # Delete employee user
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        
        # Verify user was deleted
        self.assertIsNone(User.query.get(self.employee_id))
        
        # Verify Kafka message was sent
        mock_current_app.kafka_producer.produce.assert_called_once()
        call_args = mock_current_app.kafka_producer.produce.call_args
        self.assertEqual(call_args[0][0], 'user-events')  # Check topic
        self.assertEqual(call_args[1]['key'], str(self.employee_id))  # Check key
        
        # Parse and check the message content
        message_content = json.loads(call_args[1]['value'])
        self.assertEqual(message_content['event'], 'user_deleted')
        self.assertEqual(message_content['user_id'], self.employee_id)

    @patch('app.routes.current_app')
    def test_delete_last_admin(self, mock_current_app):
        """Test attempting to delete the last admin user"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make sure there's only one admin user
        admins = User.query.filter_by(role=RoleEnum.ADMIN).all()
        for admin in admins:
            if admin.id != self.admin_id:
                db.session.delete(admin)
        db.session.commit()
        
        # Make request as admin to delete the only admin user
        response = self.client.delete(
            f'/api/users/{self.admin_id}',  # Delete admin user
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response - should be bad request
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertIn('Cannot delete the last admin user', data['error']['message'])
        
        # Verify Kafka message was NOT sent
        mock_current_app.kafka_producer.produce.assert_not_called()

    @patch('app.routes.current_app')
    def test_login(self, mock_current_app):
        """Test user login"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Login data
        login_data = {
            'email': 'admin@test.com',
            'password': 'password123'
        }
        
        # Make login request
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['email'], 'admin@test.com')
        self.assertIn('permissions', data)
        
        # Verify token can be decoded
        token = data['token']
        decoded = jwt.decode(token, self.app.config['SECRET_KEY'], algorithms=['HS256'])
        self.assertEqual(decoded['user_id'], self.admin_id)

    @patch('app.routes.current_app')
    def test_login_wrong_password(self, mock_current_app):
        """Test login with wrong password"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Login data with wrong password
        login_data = {
            'email': 'admin@test.com',
            'password': 'wrongpassword'
        }
        
        # Make login request
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(login_data),
            content_type='application/json'
        )
        
        # Check response - should be unauthorized
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    @patch('app.routes.current_app')
    def test_validate_token(self, mock_current_app):
        """Test token validation"""
        # Mock Kafka producer
        mock_current_app.kafka_producer = MagicMock()
        
        # Make validate request
        response = self.client.get(
            '/api/auth/validate',
            headers={'Authorization': f'Bearer {self.admin_token}'}
        )
        
        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['email'], 'admin@test.com')
        self.assertEqual(data['role'], 'admin')
        self.assertIn('permissions', data)

if __name__ == '__main__':
    unittest.main()