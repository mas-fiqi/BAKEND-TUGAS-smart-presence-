# app/routers/classes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.schemas.classroom import ClassCreate, ClassOut, ClassUpdate, AssignRequest, MemberOut
from app.services import class_service
from app.services import user_service
from app.routers.users import get_current_user_from_header  # reuse auth dependency
from app.schemas.user import UserOut
from typing import List

router = APIRouter()

@router.post("/", response_model=ClassOut, status_code=201)
async def create_class(payload: ClassCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user_from_header)):
    # only authenticated users allowed (you can add role check)
    # check uniqueness kode_kelas
    existing = await class_service.get_all_classes(db)
    if any(c.kode_kelas == payload.kode_kelas for c in existing):
        raise HTTPException(status_code=400, detail="Kode kelas sudah digunakan")
    kelas = await class_service.create_class(db, nama_kelas=payload.nama_kelas, kode_kelas=payload.kode_kelas)
    return ClassOut.from_orm(kelas)

@router.get("/", response_model=List[ClassOut])
async def list_classes(db: AsyncSession = Depends(get_db)):
    classes = await class_service.get_all_classes(db)
    return [ClassOut.from_orm(c) for c in classes]

@router.get("/{class_id}", response_model=ClassOut)
async def get_class(class_id: int, db: AsyncSession = Depends(get_db)):
    kelas = await class_service.get_class_by_id(db, class_id)
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    return ClassOut.from_orm(kelas)

@router.put("/{class_id}", response_model=ClassOut)
async def update_class(class_id: int, payload: ClassUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user_from_header)):
    kelas = await class_service.get_class_by_id(db, class_id)
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    kelas = await class_service.update_class(db, kelas, nama_kelas=payload.nama_kelas, kode_kelas=payload.kode_kelas)
    return ClassOut.from_orm(kelas)

@router.delete("/{class_id}", status_code=204)
async def delete_class(class_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user_from_header)):
    kelas = await class_service.get_class_by_id(db, class_id)
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    await class_service.delete_class(db, kelas)
    return {}

@router.post("/{class_id}/assign", status_code=200)
async def assign_user(class_id: int, payload: AssignRequest, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user_from_header)):
    kelas = await class_service.get_class_by_id(db, class_id)
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    user = await user_service.get_user_by_id(db, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    uc = await class_service.assign_user_to_class(db, user, kelas)
    return {"message": "User assigned", "user_id": user.id, "class_id": kelas.id}

@router.get("/{class_id}/members", response_model=List[MemberOut])
async def class_members(class_id: int, db: AsyncSession = Depends(get_db)):
    kelas = await class_service.get_class_by_id(db, class_id)
    if not kelas:
        raise HTTPException(status_code=404, detail="Kelas tidak ditemukan")
    members = await class_service.list_members(db, kelas)
    return members
