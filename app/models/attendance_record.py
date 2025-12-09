from sqlalchemy import Column, Integer, ForeignKey, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.connection import Base

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(50), nullable=False)  # e.g., hadir, tidak, terlambat
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    check_in_time = Column(DateTime(timezone=True), nullable=True)  # explicit check-in time
    method = Column(String, default="face")  # face / pin / qr / fallback

    full_name = Column(String, nullable=True)
    student_number = Column(String, nullable=True)
    actor_role = Column(String, nullable=True)  # "student" or "teacher"

    # relationships
    session = relationship("AttendanceSession", back_populates="records")
    user = relationship("User", back_populates="attendance_records")
