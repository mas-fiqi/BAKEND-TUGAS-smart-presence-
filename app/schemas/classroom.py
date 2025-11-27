# app/schemas/classroom.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

class ClassCreate(BaseModel):
    nama_kelas: str
    kode_kelas: str

class ClassUpdate(BaseModel):
    nama_kelas: Optional[str] = None
    kode_kelas: Optional[str] = None

class ClassOut(BaseModel):
    id: int
    nama_kelas: str
    kode_kelas: str

    # agar .from_orm() bekerja
    model_config = ConfigDict(from_attributes=True)

class AssignRequest(BaseModel):
    user_id: int

class MemberOut(BaseModel):
    user_id: int
    nama: str
    email: str

    # MemberOut default tidak perlu from_orm kecuali kamu memanggil from_orm pada model ini
    # model_config = ConfigDict(from_attributes=False)
