from pydantic import BaseModel
from typing import Optional

class FallbackIn(BaseModel):
    user_id: int
    pin: str

class FallbackAttendanceIn(BaseModel):
    pin: Optional[str] = None
    code: Optional[str] = None
    full_name: Optional[str] = None
    student_number: Optional[str] = None
    actor_role: Optional[str] = None

class CreateFallbackIn(BaseModel):
    pin: Optional[str] = None
    qr_code: Optional[str] = None

class FallbackOut(BaseModel):
    status: str
    user_id: int
    record_id: int | None = None
