from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class RoomType(enum.Enum):
    MEETING = "meeting"
    CONFERENCE = "conference"
    PRESENTATION = "presentation"
    WORKSHOP = "workshop"

class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    room_type = db.Column(db.Enum(RoomType), default=RoomType.MEETING, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    floor = db.Column(db.String(20), nullable=False)
    building = db.Column(db.String(100), nullable=True)
    has_projector = db.Column(db.Boolean, default=False)
    has_video_conf = db.Column(db.Boolean, default=False)
    has_whiteboard = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type.value,
            'capacity': self.capacity,
            'floor': self.floor,
            'building': self.building,
            'has_projector': self.has_projector,
            'has_video_conf': self.has_video_conf,
            'has_whiteboard': self.has_whiteboard,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class RoomUnavailability(db.Model):
    """Track times when rooms are unavailable for reasons other than reservations
    (e.g., maintenance, special events, etc.)"""
    __tablename__ = 'room_unavailability'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    room = db.relationship('Room', backref=db.backref('unavailability', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'reason': self.reason,
            'created_at': self.created_at.isoformat()
        }