
from app import create_app
from app.utils import init_kafka_consumers

app = create_app()
init_kafka_consumers()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)