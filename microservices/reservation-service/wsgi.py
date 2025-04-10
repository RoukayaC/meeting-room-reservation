from app import create_app
from app.utils import start_kafka_consumers

app = create_app()

# Start Kafka consumers for handling room and user events
start_kafka_consumers()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)