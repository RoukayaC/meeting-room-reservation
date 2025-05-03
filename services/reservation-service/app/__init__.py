from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from .models import db, Reservation, ReservationStatus, ReservationAttendee
from .routes import reservation_bp
import os
from confluent_kafka import Producer, Consumer, KafkaError
import logging
import threading
import json
from datetime import datetime, timedelta
import sys

# Add the shared directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../shared')))

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
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URI', 'postgresql://postgres:postgres@db:5432/reservation_service'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        KAFKA_BOOTSTRAP_SERVERS=os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        USER_SERVICE_URL=os.environ.get('USER_SERVICE_URL', 'http://user-service:5000'),
        ROOM_SERVICE_URL=os.environ.get('ROOM_SERVICE_URL', 'http://room-service:5000')
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
    
    # Register blueprints
    app.register_blueprint(reservation_bp)
    
    # Kafka Producer setup
    kafka_config = {
        'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
        'client.id': 'reservation_service'
    }
    app.kafka_producer = Producer(kafka_config)
    
    # Setup OpenTelemetry if not in testing mode
    if not config or not config.get('TESTING'):
        try:
            otel_components = setup_otel(app, 'reservation-service')
            setup_request_hooks(app, otel_components['request_counter'], otel_components['error_counter'])
            app.logger.info("OpenTelemetry instrumentation set up")
        except Exception as e:
            app.logger.warning(f"Failed to setup OpenTelemetry: {str(e)}")
    
    # Create tables if they don't exist (development only)
    with app.app_context():
        db.create_all()
    
    # Setup automatic completion of past reservations
    def update_completed_reservations():
        with app.app_context():
            now = datetime.utcnow()
            past_reservations = Reservation.query.filter(
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.end_time < now
            ).all()
            
            for reservation in past_reservations:
                reservation.status = ReservationStatus.COMPLETED
            
            if past_reservations:
                app.logger.info(f"Marked {len(past_reservations)} past reservations as completed")
                db.session.commit()
                
                # Publish events to Kafka
                for reservation in past_reservations:
                    try:
                        app.kafka_producer.produce(
                            'reservation-events',
                            key=str(reservation.id),
                            value=json.dumps({
                                'event': 'reservation_completed',
                                'reservation_id': reservation.id,
                                'room_id': reservation.room_id,
                                'user_id': reservation.user_id
                            })
                        )
                    except Exception as e:
                        app.logger.error(f"Failed to publish completion event: {str(e)}")
                
                app.kafka_producer.flush()
    
    # Start Kafka consumer in a separate thread
    def start_kafka_consumer():
        consumer_config = {
            'bootstrap.servers': app.config['KAFKA_BOOTSTRAP_SERVERS'],
            'group.id': 'reservation_service_group',
            'auto.offset.reset': 'earliest'
        }
        
        consumer = Consumer(consumer_config)
        consumer.subscribe(['room-events', 'user-events'])
        
        app.logger.info("Kafka consumer started for room-events and user-events")
        
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
                            
                            # Handle room-events
                            if msg.topic() == 'room-events':
                                if value.get('event') == 'room_deleted':
                                    # Cancel reservations for deleted room
                                    room_id = value.get('room_id')
                                    if room_id:
                                        future_reservations = Reservation.query.filter(
                                            Reservation.room_id == room_id,
                                            Reservation.status == ReservationStatus.CONFIRMED,
                                            Reservation.start_time > datetime.utcnow()
                                        ).all()
                                        
                                        for reservation in future_reservations:
                                            reservation.status = ReservationStatus.CANCELLED
                                        
                                        if future_reservations:
                                            app.logger.info(f"Cancelled {len(future_reservations)} reservations for deleted room {room_id}")
                                            db.session.commit()
                                            
                                            # Publish cancellation events
                                            for reservation in future_reservations:
                                                app.kafka_producer.produce(
                                                    'reservation-events',
                                                    key=str(reservation.id),
                                                    value=json.dumps({
                                                        'event': 'reservation_cancelled',
                                                        'reservation_id': reservation.id,
                                                        'room_id': reservation.room_id,
                                                        'user_id': reservation.user_id,
                                                        'reason': 'Room deleted'
                                                    })
                                                )
                                            
                                            app.kafka_producer.flush()
                            
                            # Handle user-events
                            elif msg.topic() == 'user-events':
                                if value.get('event') == 'user_deleted':
                                    # Cancel future reservations for deleted user
                                    user_id = value.get('user_id')
                                    if user_id:
                                        future_reservations = Reservation.query.filter(
                                            Reservation.user_id == user_id,
                                            Reservation.status == ReservationStatus.CONFIRMED,
                                            Reservation.start_time > datetime.utcnow()
                                        ).all()
                                        
                                        for reservation in future_reservations:
                                            reservation.status = ReservationStatus.CANCELLED
                                        
                                        if future_reservations:
                                            app.logger.info(f"Cancelled {len(future_reservations)} reservations for deleted user {user_id}")
                                            db.session.commit()
                                            
                                            # Publish cancellation events
                                            for reservation in future_reservations:
                                                app.kafka_producer.produce(
                                                    'reservation-events',
                                                    key=str(reservation.id),
                                                    value=json.dumps({
                                                        'event': 'reservation_cancelled',
                                                        'reservation_id': reservation.id,
                                                        'room_id': reservation.room_id,
                                                        'user_id': reservation.user_id,
                                                        'reason': 'User deleted'
                                                    })
                                                )
                                            
                                            app.kafka_producer.flush()
                    except Exception as e:
                        app.logger.error(f"Error processing message: {str(e)}")
        except Exception as e:
            app.logger.error(f"Kafka consumer error: {str(e)}")
        finally:
            consumer.close()
    
    # Start consumer thread if not in testing mode
    if not config or not config.get('TESTING'):
        # Run update_completed_reservations once at startup
        update_completed_reservations()
        
        # Start consumer thread
        consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
        consumer_thread.start()
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'reservation-service'}, 200
    
    return app