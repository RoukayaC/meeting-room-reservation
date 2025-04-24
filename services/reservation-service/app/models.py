from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class ReservationStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class Reservation(db.Model):
    __tablename__ = 'reservations'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(ReservationStatus), default=ReservationStatus.CONFIRMED, nullable=False)
    attendees_count = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'status': self.status.value,
            'attendees_count': self.attendees_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @property
    def is_active(self):
        """Check if reservation is currently active (not cancelled or completed)"""
        return self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]
    
    @property
    def is_past(self):
        """Check if reservation is in the past"""
        return self.end_time < datetime.utcnow()

class ReservationAttendee(db.Model):
    __tablename__ = 'reservation_attendees'
    
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=True)  # Nullable for external attendees
    email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    reservation = db.relationship('Reservation', backref=db.backref('attendees', lazy=True, cascade="all, delete-orphan"))
    
    def to_dict(self):
        return {
            'id': self.id,
            'reservation_id': self.reservation_id,
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat()
        }