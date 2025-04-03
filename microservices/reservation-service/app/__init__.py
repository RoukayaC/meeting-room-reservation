
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import os

db = SQLAlchemy()
jwt = JWTManager()
metrics = PrometheusMetrics.for_app_factory()

def create_app():
    app = Flask(__name__)
    CORS(app)
    metrics.init_app(app)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@postgres:5432/reservations')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'super-secret-key')
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    
    # Register blueprints
    from app.routes import reservation_bp
    app.register_blueprint(reservation_bp)
    
    # Health check endpoint
    @app.route('/api/reservations/health')
    def health():
        return {'status': 'healthy'}
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
