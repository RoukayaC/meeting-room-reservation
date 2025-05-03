from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
import os
from confluent_kafka import Producer, Consumer, KafkaError
import logging
import threading
import json
import sys

# Add the shared directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shared')))

# Import models
from .models import db, Room, RoomType, RoomUnavailability

# Import from shared utils
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
    def ensure_database_exists(db_uri, logger):
        """Dummy function if shared module fails to import"""
        logger.warning("Using dummy database creation function - shared module failed to import")
        return True

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
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URI', 'postgresql://postgres:postgres@localhost:5432/room_service'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        USER_SERVICE_URL=os.environ.get('USER_SERVICE_URL', 'http://user-service:5000'),
        RESERVATION_SERVICE_URL=os.environ.get('RESERVATION_SERVICE_URL', 'http://reservation-service:5000')
    )
    
    # Override config if provided
    if config:
        app.config.update(config)
    
    # Create database if it doesn't exist
    target_db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    app.logger.info(f"Target database URI: {target_db_uri}")
    if not ensure_database_exists(target_db_uri, app.logger):
        app.logger.warning("Failed to ensure database exists. Application might not function correctly.")
        # Uncomment to halt startup on database creation failure
        # raise RuntimeError("Database could not be verified or created.")
    
    # Initialize extensions
    CORS(app)
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Import routes here to avoid circular imports
    from .routes import room_bp
    
    # Register blueprints
    app.register_blueprint(room_bp)
    
    # Kafka Producer setup
    kafka_config = {
        'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
        'client.id': 'room_service'
    }
    app.kafka_producer = Producer(kafka_config)
    
    # Setup OpenTelemetry if not in testing mode
    if not config or not config.get('TESTING'):
        try:
            otel_components = setup_otel(app, 'room-service')
            setup_request_hooks(app, otel_components['request_counter'], otel_components['error_counter'])
            app.logger.info("OpenTelemetry instrumentation set up")
        except Exception as e:
            app.logger.warning(f"Failed to setup OpenTelemetry: {str(e)}")
    
    # Create tables if they don't exist (development only)
    with app.app_context():
        db.create_all()
        
        # Create sample rooms if none exist and not in testing with SKIP_SAMPLE_DATA
        if Room.query.count() == 0 and not app.config.get('SKIP_SAMPLE_DATA', False):
            sample_rooms = [
                Room(
                    name="Meeting Room A",
                    room_type=RoomType.MEETING,
                    capacity=8,
                    floor="1st",
                    building="Main Building",
                    has_projector=True,
                    has_video_conf=True
                ),
                Room(
                    name="Conference Room 1",
                    room_type=RoomType.CONFERENCE,
                    capacity=20,
                    floor="2nd",
                    building="Main Building",
                    has_projector=True,
                    has_video_conf=True,
                    has_whiteboard=True
                ),
                Room(
                    name="Workshop Space",
                    room_type=RoomType.WORKSHOP,
                    capacity=30,
                    floor="Ground",
                    building="Annex",
                    has_whiteboard=True
                )
            ]
            
            for room in sample_rooms:
                db.session.add(room)
            
            db.session.commit()
            app.logger.info(f"Created {len(sample_rooms)} sample rooms")
    
    # Start Kafka consumer in a separate thread
    def start_kafka_consumer():
        consumer_config = {
            'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
            'group.id': 'room_service_group',
            'auto.offset.reset': 'earliest'
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(['reservation-events'])
        
        app.logger.info("Kafka consumer started for reservation-events")
        
        try:
            while True:
                msg = consumer.poll(1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        app.logger.info(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                    else:
                        app.logger.error(f"Kafka consumer error: {msg.error()}")
                else:
                    try:
                        # Process the message
                        with app.app_context():
                            value = json.loads(msg.value().decode('utf-8'))
                            app.logger.info(f"Received message: {value}")
                            
                            # Handle reservation events if needed
                            # This can be used to update room availability status or statistics
                    except Exception as e:
                        app.logger.error(f"Error processing message: {str(e)}")
        except Exception as e:
            app.logger.error(f"Kafka consumer error: {str(e)}")
        finally:
            consumer.close()
      # Start consumer thread if not in testing mode
    if not config or not config.get('TESTING'):
        consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
        consumer_thread.start()

    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'room-service'}, 200
    
    return app