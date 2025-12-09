# app/schemas/session.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time, datetime

class SessionCreate(BaseModel):
    class_id: int
    tanggal: date
    jam_mulai: Optional[str] = None  # "HH:MM:SS" atau None
    jam_selesai: Optional[str] = None

class SessionOut(BaseModel):
    id: int
    class_id: int
    tanggal: date
    jam_mulai: Optional[time] = None
    jam_selesai: Optional[time] = None
    status: str
    attendance_count: Optional[int] = 0

    # agar .from_orm() bekerja di Pydantic v2
    model_config = ConfigDict(from_attributes=True)

class FallbackRequest(BaseModel):
    user_id: int
    pin: str

class PinAttendanceRequest(BaseModel):
    pin: str
    full_name: Optional[str] = None
    student_number: Optional[str] = None
    actor_role: Optional[str] = None

class AttendanceResult(BaseModel):
    status: str
    user_id: Optional[int] = None
    score: Optional[float] = None

class AttendanceRecordOut(BaseModel):
    id: int
    session_id: int
    user_id: int
    status: str
    timestamp: datetime
    check_in_time: Optional[datetime] = None
    method: str
    full_name: Optional[str] = None
    student_number: Optional[str] = None
    actor_role: Optional[str] = None
    user_name: Optional[str] = None  # from user table

    model_config = ConfigDict(from_attributes=True)

class AttendanceHistoryOut(BaseModel):
    id: int
    session_id: int
    class_name: str
    date: str  # YYYY-MM-DD
    status: str  # present / late / absent
    method: Optional[str] = None
    check_in_time: str  # ISO format
    session_name: Optional[str] = None
    photo_url: Optional[str] = None
