from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum

db = SQLAlchemy()

class RoleEnum(enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"
    VISITOR = "visitor"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum(RoleEnum), default=RoleEnum.EMPLOYEE, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # OAuth related fields
    oauth_provider = db.Column(db.String(50), nullable=True)
    oauth_id = db.Column(db.String(255), nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """Check if user has admin role"""
        return self.role == RoleEnum.ADMIN
    
    @property
    def is_employee(self):
        """Check if user has employee role"""
        return self.role == RoleEnum.EMPLOYEE
    
    @property
    def is_visitor(self):
        """Check if user has visitor role"""
        return self.role == RoleEnum.VISITOR
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value,
            'department': self.department,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Permission(db.Model):
    """Permission model for RBAC"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }

class RolePermission(db.Model):
    """Association table between roles and permissions"""
    __tablename__ = 'role_permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.Enum(RoleEnum), nullable=False)
    permission_id = db.Column(db.Integer, db.ForeignKey('permissions.id'), nullable=False)
    
    # Direct relationship to Permission
    permission = db.relationship('Permission', backref=db.backref('role_permissions', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('role', 'permission_id', name='unique_role_permission'),
    )