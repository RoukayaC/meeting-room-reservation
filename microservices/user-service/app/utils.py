import logging
import json
from kafka import KafkaProducer
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('user-service')

# Configure Kafka
KAFKA_BROKER_URL = os.getenv('KAFKA_BROKER_URL', 'kafka:9092')
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