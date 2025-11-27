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

    # agar .from_orm() bekerja di Pydantic v2
    model_config = ConfigDict(from_attributes=True)

class FallbackRequest(BaseModel):
    user_id: int
    pin: str

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

    model_config = ConfigDict(from_attributes=True)
