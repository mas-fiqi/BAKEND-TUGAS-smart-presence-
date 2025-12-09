# app/schemas/user.py
from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    nama: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    nama: str
    email: EmailStr
    role: str
    is_active: bool
    profile_image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    # untuk mendukung .from_orm() di Pydantic v2
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None

class UserUpdate(BaseModel):
    nama: Optional[str] = None
