import logging
import json
import threading
from kafka import KafkaProducer, KafkaConsumer
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('room-service')

# Configure Kafka
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'kafka:9092')
ROOM_TOPIC = 'room-events'
USER_TOPIC = 'user-events'

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

def start_kafka_consumer():
    """Start a Kafka consumer for user events."""
    try:
        consumer = KafkaConsumer(
            USER_TOPIC,
            bootstrap_servers=KAFKA_BROKER_URL,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='room-service-group'
        )
        
        logger.info(f"Kafka consumer started for topic {USER_TOPIC}")
        
        for message in consumer:
            try:
                process_user_event(message.value)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
    
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer: {str(e)}")

def process_user_event(event):
    """Process user events from Kafka."""
    event_type = event.get('event_type')
    data = event.get('data')
    
    logger.info(f"Processing user event: {event_type}")
    
    # Currently no specific actions needed for user events in room service
    # This is a placeholder for future functionality
    pass

# Start Kafka consumer in a separate thread
def init_kafka_consumers():
    consumer_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    consumer_thread.start()