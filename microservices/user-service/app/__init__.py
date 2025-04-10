from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from .models import db, User, RoleEnum
from .routes import user_bp
from .auth import auth_bp
import os
from confluent_kafka import Producer
import logging

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
        
        # Create admin user if not exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'adminpassword')
        
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
    
    return app