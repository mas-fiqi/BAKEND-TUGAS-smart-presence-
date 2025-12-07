# app/schemas/classroom.py
from pydantic import BaseModel, ConfigDict, model_validator
from typing import Optional

class ClassCreate(BaseModel):
    nama_kelas: Optional[str] = None
    kode_kelas: Optional[str] = None
    name: Optional[str] = None  # alias for Flutter compatibility
    code: Optional[str] = None  # alias for Flutter compatibility

    @model_validator(mode='after')
    def validate_fields(self):
        # Map Flutter fields to backend fields
        if self.name and not self.nama_kelas:
            self.nama_kelas = self.name
        if self.code and not self.kode_kelas:
            self.kode_kelas = self.code

        # Ensure required fields are present
        if not self.nama_kelas or not self.kode_kelas:
            raise ValueError("nama_kelas/kode_kelas or name/code fields are required")

        return self

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
