from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class ClassRoom(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    nama_kelas = Column(String(255), nullable=False)
    kode_kelas = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user_classes = relationship("UserClass", back_populates="kelas", cascade="all, delete-orphan")
    sessions = relationship("AttendanceSession", back_populates="kelas", cascade="all, delete-orphan")
