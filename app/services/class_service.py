# app/services/class_service.py
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.models.classroom import ClassRoom
from app.models.user_class import UserClass
from app.models.user import User

async def create_class(db: AsyncSession, nama_kelas: str, kode_kelas: str) -> ClassRoom:
    kelas = ClassRoom(nama_kelas=nama_kelas, kode_kelas=kode_kelas)
    db.add(kelas)
    await db.flush()
    await db.commit()
    await db.refresh(kelas)
    return kelas

async def get_class_by_id(db: AsyncSession, class_id: int) -> Optional[ClassRoom]:
    stmt = select(ClassRoom).where(ClassRoom.id == class_id)
    res = await db.execute(stmt)
    return res.scalars().first()

async def get_all_classes(db: AsyncSession) -> List[ClassRoom]:
    stmt = select(ClassRoom)
    res = await db.execute(stmt)
    return res.scalars().all()

async def update_class(db: AsyncSession, kelas: ClassRoom, nama_kelas: Optional[str]=None, kode_kelas: Optional[str]=None) -> ClassRoom:
    if nama_kelas is not None:
        kelas.nama_kelas = nama_kelas
    if kode_kelas is not None:
        kelas.kode_kelas = kode_kelas
    db.add(kelas)
    await db.commit()
    await db.refresh(kelas)
    return kelas

async def delete_class(db: AsyncSession, kelas: ClassRoom):
    await db.delete(kelas)
    await db.commit()
    return True

async def assign_user_to_class(db: AsyncSession, user: User, kelas: ClassRoom) -> UserClass:
    # check existing
    stmt = select(UserClass).where(UserClass.user_id == user.id, UserClass.class_id == kelas.id)
    res = await db.execute(stmt)
    existing = res.scalars().first()
    if existing:
        return existing
    uc = UserClass(user_id=user.id, class_id=kelas.id)
    db.add(uc)
    await db.flush()
    await db.commit()
    await db.refresh(uc)
    return uc

async def list_members(db: AsyncSession, kelas: ClassRoom):
    # join user_classes -> users
    stmt = select(User.id, User.nama, User.email).join(UserClass, User.id == UserClass.user_id).where(UserClass.class_id == kelas.id)
    res = await db.execute(stmt)
    rows = res.all()
    members = [{"user_id": r[0], "nama": r[1], "email": r[2]} for r in rows]
    return members
