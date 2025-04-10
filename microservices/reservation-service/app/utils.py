import logging
import json
import threading
import requests
from kafka import KafkaProducer, KafkaConsumer
import os
from functools import wraps
from app.models import Reservation
from app import db
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('reservation-service')

# Configure Kafka
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'kafka:9092')
RESERVATION_TOPIC = 'reservation-events'
ROOM_TOPIC = 'room-events'
USER_TOPIC = 'user-events'

# Service URLs
ROOM_SERVICE_URL = os.getenv('ROOM_SERVICE_URL', 'http://room-service:5000')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user-service:5000')

try:
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER_URL,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    logger.info("Kafka producer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Kafka producer: {str(e)}")
    producer = None

def publish_message(topic, event_type, data):
    """Publish a message to Kafka topic."""
    if producer:
        try:
            producer.send(topic, {
                'event_type': event_type,
                'data': data
            })
            logger.info(f"Message published to topic {topic}: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish message: {str(e)}")
    else:
        logger.warning("Kafka producer not available, message not published")

def start_kafka_consumers():
    """Start Kafka consumers for room and user events."""
    try:
        # Create consumer for room events
        room_consumer = KafkaConsumer(
            ROOM_TOPIC,
            bootstrap_servers=KAFKA_BROKER_URL,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='reservation-service-room-group'
        )
        
        # Create consumer for user events
        user_consumer = KafkaConsumer(
            USER_TOPIC,
            bootstrap_servers=KAFKA_BROKER_URL,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='reservation-service-user-group'
        )
        
        logger.info(f"Kafka consumers started for topics {ROOM_TOPIC} and {USER_TOPIC}")
        
        # Start consumer threads
        threading.Thread(target=consume_room_events, args=(room_consumer,), daemon=True).start()
        threading.Thread(target=consume_user_events, args=(user_consumer,), daemon=True).start()
    
    except Exception as e:
        logger.error(f"Failed to start Kafka consumers: {str(e)}")

def consume_room_events(consumer):
    """Consume room events from Kafka."""
    for message in consumer:
        try:
            process_room_event(message.value)
        except Exception as e:
            logger.error(f"Error processing room event: {str(e)}")

def consume_user_events(consumer):
    """Consume user events from Kafka."""
    for message in consumer:
        try:
            process_user_event(message.value)
        except Exception as e:
            logger.error(f"Error processing user event: {str(e)}")

def process_room_event(event):
    """Process room events from Kafka."""
    event_type = event.get('event_type')
    data = event.get('data')
    
    logger.info(f"Processing room event: {event_type}")
    
    if event_type == 'ROOM_DELETED' or (event_type == 'ROOM_STATUS_UPDATED' and not data.get('active', True)):
        # If a room is deleted or deactivated, cancel all future reservations for that room
        room_id = data.get('room_id')
        if room_id:
            try:
                cancel_reservations_for_room(room_id)
            except Exception as e:
                logger.error(f"Failed to cancel reservations for room {room_id}: {str(e)}")

def process_user_event(event):
    """Process user events from Kafka."""
    event_type = event.get('event_type')
    data = event.get('data')
    
    logger.info(f"Processing user event: {event_type}")
    
    if event_type == 'USER_STATUS_UPDATED' and not data.get('active', True):
        # If a user is deactivated, cancel all their future reservations
        user_id = data.get('user_id')
        if user_id:
            try:
                cancel_reservations_for_user(user_id)
            except Exception as e:
                logger.error(f"Failed to cancel reservations for user {user_id}: {str(e)}")

def cancel_reservations_for_room(room_id):
    """Cancel all future reservations for a specific room."""
    now = datetime.utcnow()
    future_reservations = Reservation.query.filter(
        Reservation.room_id == room_id,
        Reservation.start_time > now,
        Reservation.status == 'CONFIRMED'
    ).all()
    
    for reservation in future_reservations:
        reservation.status = 'CANCELLED'
        
        # Publish reservation cancelled event
        publish_message(RESERVATION_TOPIC, 'RESERVATION_CANCELLED', {
            'reservation_id': reservation.id,
            'reason': 'Room deactivated or deleted'
        })
    
    db.session.commit()
    logger.info(f"Cancelled {len(future_reservations)} future reservations for room {room_id}")

def cancel_reservations_for_user(user_id):
    """Cancel all future reservations for a specific user."""
    now = datetime.utcnow()
    future_reservations = Reservation.query.filter(
        Reservation.user_id == user_id,
        Reservation.start_time > now,
        Reservation.status == 'CONFIRMED'
    ).all()
    
    for reservation in future_reservations:
        reservation.status = 'CANCELLED'
        
        # Publish reservation cancelled event
        publish_message(RESERVATION_TOPIC, 'RESERVATION_CANCELLED', {
            'reservation_id': reservation.id,
            'reason': 'User deactivated'
        })
    
    db.session.commit()
    logger.info(f"Cancelled {len(future_reservations)} future reservations for user {user_id}")

# Role-based access control decorator
def role_required(*roles):
    """Decorator to check if user has required role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_jwt_extended import get_jwt_identity
            current_user = get_jwt_identity()
            if current_user.get('role') not in roles:
                return {'error': 'Unauthorized access'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator