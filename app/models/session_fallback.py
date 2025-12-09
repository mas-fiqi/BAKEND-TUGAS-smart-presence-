# app/models/session_fallback.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database.connection import Base

class SessionFallback(Base):
    __tablename__ = "session_fallbacks"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False)
    pin = Column(String(64), nullable=False)
    qr_code = Column(String(128), nullable=True)  # Optional QR code for session
    created_at = Column(DateTime(timezone=True), server_default=func.now())
