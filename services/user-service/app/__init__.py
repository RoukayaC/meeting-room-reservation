from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_cors import CORS
import os
import logging
from confluent_kafka import Producer
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from urllib.parse import urlparse

# Add the shared directory to the Python path if not already added
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shared')))

# Import local models and blueprints
from .models import db, User, RoleEnum, Permission, RolePermission
from .routes import user_bp
from .auth import auth_bp

# Import shared utilities
try:
    from shared.opentelemetry_utils import setup_otel, setup_request_hooks
    from shared.db_utils import ensure_database_exists
except ImportError as e:
    logging.warning(f"Could not import shared utilities: {e}. Some features might be limited.")
    # Define dummy functions if import fails
    def setup_otel(app, service_name):
        return {"request_counter": type('obj', (object,), {'add': lambda *args, **kwargs: None})(),
                "error_counter": type('obj', (object,), {'add': lambda *args, **kwargs: None})()}
    def setup_request_hooks(app, req_counter, err_counter):
        pass
    
    # Local fallback implementation for ensure_database_exists
    def ensure_database_exists(db_uri, logger):
        """Checks if the database exists and creates it if not."""
        # This is just a fallback - implementation is in shared/db_utils.py
        logger.warning("Using local fallback for database creation - shared module failed to import")
        return True

def create_error_response(message, error_code):
    """Create a standardized error response"""
    return {
        "error": {
            "message": message,
            "code": error_code
        }
    }

# --- Main Application Factory ---
def create_app(config=None):
    app = Flask(__name__)

    # Configure logging early
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app.logger.info("Initializing User Service...")

    # --- Configuration Loading ---
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev_key_user_service_replace_me'), # Use a more specific default
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/user_service'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        OAUTH_CLIENT_ID=os.environ.get('OAUTH_CLIENT_ID', ''),
        OAUTH_CLIENT_SECRET=os.environ.get('OAUTH_CLIENT_SECRET', ''),
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    )

    # Override config if provided (e.g., for testing)
    if config:
        app.config.update(config)
        app.logger.info("Applying provided configuration overrides.")

    # --- Database Auto-Creation ---
    target_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.logger.info(f"Target database URI: {target_db_uri}")
    if not ensure_database_exists(target_db_uri, app.logger):
         # Decide how to handle failure: log and continue (might fail later), or exit/raise
         app.logger.warning("Failed to ensure database exists. Application might not function correctly.")
         # raise RuntimeError("Database could not be verified or created.") # Option to halt startup

    # --- Initialize Extensions ---
    app.logger.info("Initializing Flask extensions...")
    CORS(app)
    db.init_app(app) # Initialize SQLAlchemy with the app
    migrate = Migrate(app, db) # Initialize Flask-Migrate

    # --- Kafka Producer Setup ---
    kafka_config = {
        'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
        'client.id': 'user_service',
        # Add error handling callback for Kafka
        'error_cb': lambda err: app.logger.error(f'Kafka Error: {err}')
    }
    try:
        app.kafka_producer = Producer(kafka_config)
        app.logger.info(f"Kafka producer configured for servers: {app.config['KAFKA_BOOTSTRAP_SERVERS']}")
    except Exception as e:
        app.logger.error(f"Failed to initialize Kafka producer: {e}")
        app.kafka_producer = None # Set to None to avoid errors later if needed

    # --- Register Blueprints ---
    app.register_blueprint(user_bp)
    app.register_blueprint(auth_bp)
    app.logger.info("Blueprints registered.")

    # --- OpenTelemetry Setup ---
    if not app.config.get('TESTING'): # Don't setup OTel during testing unless specified
        try:
            otel_components = setup_otel(app, 'user-service')
            setup_request_hooks(app, otel_components['request_counter'], otel_components['error_counter'])
            app.logger.info("OpenTelemetry instrumentation set up successfully.")
        except Exception as e:
            app.logger.warning(f"Failed to setup OpenTelemetry: {str(e)}")
    else:
        app.logger.info("Skipping OpenTelemetry setup in TESTING mode.")


    # --- Database Initialization (Tables, Default Data) ---
    with app.app_context():
        app.logger.info("Ensuring database tables and default data exist...")
        try:
            # Create tables based on models if they don't exist
            db.create_all()
            app.logger.info("Database tables checked/created.")

            # --- Default Permissions Setup (Idempotent) ---
            required_permissions = [
                ('user:read', 'View user details'), ('user:create', 'Create new users'),
                ('user:update', 'Update user details'), ('user:delete', 'Delete users'),
                ('user:list', 'List all users'), ('room:read', 'View room details'),
                ('room:create', 'Create new rooms'), ('room:update', 'Update room details'),
                ('room:delete', 'Delete rooms'), ('room:list', 'List all rooms'),
                ('reservation:read', 'View reservation details'), ('reservation:create', 'Create new reservations'),
                ('reservation:update', 'Update reservation details'), ('reservation:cancel', 'Cancel reservations'),
                ('reservation:list', 'List all reservations')
            ]
            permissions_map = {p.name: p for p in Permission.query.all()}
            new_permissions_added = False
            for name, desc in required_permissions:
                if name not in permissions_map:
                    new_perm = Permission(name=name, description=desc)
                    db.session.add(new_perm)
                    permissions_map[name] = new_perm # Add to map for role assignment
                    new_permissions_added = True
            if new_permissions_added:
                db.session.commit()
                app.logger.info("Added missing default permissions.")

            # --- Default Role Permissions Setup (Idempotent) ---
            admin_perm_names = [p[0] for p in required_permissions] # All perms for admin
            employee_perm_names = [
                'user:read', 'room:read', 'room:list', 'reservation:read',
                'reservation:create', 'reservation:update', 'reservation:cancel', 'reservation:list'
            ]
            visitor_perm_names = ['user:read', 'room:read', 'room:list', 'reservation:read', 'reservation:list']

            roles_to_setup = {
                RoleEnum.ADMIN: admin_perm_names,
                RoleEnum.EMPLOYEE: employee_perm_names,
                RoleEnum.VISITOR: visitor_perm_names
            }
            current_role_perms = {(rp.role, rp.permission_id) for rp in RolePermission.query.all()}
            new_role_perms_added = False

            for role, perm_names in roles_to_setup.items():
                for name in perm_names:
                    permission = permissions_map.get(name)
                    if permission and (role, permission.id) not in current_role_perms:
                        db.session.add(RolePermission(role=role, permission=permission))
                        new_role_perms_added = True

            if new_role_perms_added:
                db.session.commit()
                app.logger.info("Assigned missing default permissions to roles.")

            # --- Default Users Setup (Idempotent) ---
            # Admin User
            admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
            if not User.query.filter_by(email=admin_email).first():
                admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
                admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
                admin = User(email=admin_email, username=admin_username, first_name='Admin', last_name='User', role=RoleEnum.ADMIN)
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                app.logger.info(f"Default admin user created: {admin_email}")

            # Employee User (for testing/demo)
            employee_email = os.environ.get('EMPLOYEE_EMAIL', 'employee@example.com')
            if not User.query.filter_by(email=employee_email).first():
                employee_username = os.environ.get('EMPLOYEE_USERNAME', 'employee')
                employee_password = os.environ.get('EMPLOYEE_PASSWORD', 'employeepassword')
                employee = User(email=employee_email, username=employee_username, first_name='Test', last_name='Employee', role=RoleEnum.EMPLOYEE)
                employee.set_password(employee_password)
                db.session.add(employee)
                db.session.commit()
                app.logger.info(f"Default employee user created: {employee_email}")

        except Exception as e:
            app.logger.error(f"Error during database initialization (tables/defaults): {e}")
            # Depending on severity, you might want to raise an error
            # raise RuntimeError("Failed to initialize database tables or default data.") from e

    # --- Health Check Endpoint ---
    @app.route('/health')
    def health_check():
        # Add checks for DB connection, Kafka connection if needed
        # For now, just indicates the app is running
        return jsonify({'status': 'healthy', 'service': 'user-service'}), 200

    # --- Error Handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(create_error_response("Resource not found", "NOT_FOUND")), 404

    @app.errorhandler(500)
    def server_error(e):
        # Log the actual error
        app.logger.error(f"Internal Server Error: {e}", exc_info=True)
        return jsonify(create_error_response("Internal server error", "SERVER_ERROR")), 500

    app.logger.info("User Service initialization complete.")
    return app
