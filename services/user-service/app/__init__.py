from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
from .models import db, User, RoleEnum, Permission, RolePermission
from .routes import user_bp
from .auth import auth_bp
import os
from confluent_kafka import Producer
import logging
from shared.opentelemetry_utils import setup_otel, setup_request_hooks

def create_error_response(message, error_code):
    """Create a standardized error response"""
    return {
        "error": {
            "message": message,
            "code": error_code
        }
    }

def create_app(config=None):
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/user_service'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        OAUTH_CLIENT_ID=os.environ.get('OAUTH_CLIENT_ID', ''),
        OAUTH_CLIENT_SECRET=os.environ.get('OAUTH_CLIENT_SECRET', ''),
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    )
    
    # Override config if provided
    if config:
        app.config.update(config)
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)
    
    # Kafka Producer setup
    kafka_config = {
        'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
        'client.id': 'user_service'
    }
    app.kafka_producer = Producer(kafka_config)
    

    
    # Create tables if they don't exist (development only)
    with app.app_context():
        db.create_all()
            # Setup OpenTelemetry if not in testing mode
        if not config or not config.get('TESTING'):
            try:
                otel_components = setup_otel(app, 'user-service')
                setup_request_hooks(app, otel_components['request_counter'], otel_components['error_counter'])
                app.logger.info("OpenTelemetry instrumentation set up")
            except Exception as e:
                app.logger.warning(f"Failed to setup OpenTelemetry: {str(e)}")
        # Create default permissions if they don't exist
        if Permission.query.count() == 0:
            permissions = [
                Permission(name='user:read', description='View user details'),
                Permission(name='user:create', description='Create new users'),
                Permission(name='user:update', description='Update user details'),
                Permission(name='user:delete', description='Delete users'),
                Permission(name='user:list', description='List all users'),
                Permission(name='room:read', description='View room details'),
                Permission(name='room:create', description='Create new rooms'),
                Permission(name='room:update', description='Update room details'),
                Permission(name='room:delete', description='Delete rooms'),
                Permission(name='room:list', description='List all rooms'),
                Permission(name='reservation:read', description='View reservation details'),
                Permission(name='reservation:create', description='Create new reservations'),
                Permission(name='reservation:update', description='Update reservation details'),
                Permission(name='reservation:cancel', description='Cancel reservations'),
                Permission(name='reservation:list', description='List all reservations')
            ]
            
            for permission in permissions:
                db.session.add(permission)
            
            db.session.commit()
            app.logger.info(f"Created {len(permissions)} default permissions")
            
            # Assign permissions to roles
            admin_permissions = Permission.query.all()
            for permission in admin_permissions:
                role_permission = RolePermission(role=RoleEnum.ADMIN, permission=permission)
                db.session.add(role_permission)
            
            # Employee permissions
            employee_permission_names = [
                'user:read', 'room:read', 'room:list',
                'reservation:read', 'reservation:create', 'reservation:update',
                'reservation:cancel', 'reservation:list'
            ]
            
            employee_permissions = Permission.query.filter(Permission.name.in_(employee_permission_names)).all()
            for permission in employee_permissions:
                role_permission = RolePermission(role=RoleEnum.EMPLOYEE, permission=permission)
                db.session.add(role_permission)
            
            # Visitor permissions
            visitor_permission_names = [
                'user:read', 'room:read', 'room:list',
                'reservation:read', 'reservation:list'
            ]
            
            visitor_permissions = Permission.query.filter(Permission.name.in_(visitor_permission_names)).all()
            for permission in visitor_permissions:
                role_permission = RolePermission(role=RoleEnum.VISITOR, permission=permission)
                db.session.add(role_permission)
            
            db.session.commit()
            app.logger.info("Assigned default permissions to roles")
        
        # Create admin user if not exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
        
        # If in testing mode and a test admin exists, don't create another one
        if config and config.get('TESTING') and User.query.filter_by(role=RoleEnum.ADMIN).first():
            app.logger.info("Test admin user detected, skipping default admin creation")
        else:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(
                    email=admin_email,
                    first_name='Admin',
                    last_name='User',
                    role=RoleEnum.ADMIN
                )
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                app.logger.info(f"Admin user created: {admin_email}")
    
    @app.route('/health')
    def health_check():
        return {'status': 'healthy'}
        
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(create_error_response("Resource not found", "NOT_FOUND")), 404
        
    @app.errorhandler(500)
    def server_error(e):
        return jsonify(create_error_response("Internal server error", "SERVER_ERROR")), 500
    
    return app