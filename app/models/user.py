from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='user', nullable=False)
    face_embedding = Column(JSON, nullable=True)  # list of floats (embedding), portable across DB
    profile_image_url = Column(String(500), nullable=True)  # URL to profile image
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_classes = relationship('UserClass', back_populates='user', cascade='all, delete-orphan')
    attendance_records = relationship('AttendanceRecord', back_populates='user', cascade='all, delete-orphan')
