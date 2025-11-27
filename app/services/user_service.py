# app/services/user_service.py
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from passlib.hash import pbkdf2_sha256
from typing import Optional

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    stmt = select(User).where(User.email == email)
    res = await db.execute(stmt)
    return res.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    return res.scalars().first()

async def create_user(db: AsyncSession, nama: str, email: str, password: str, role: str = "user") -> User:
    hashed = pbkdf2_sha256.hash(password)
    user = User(nama=nama, email=email, password_hash=hashed, role=role)
    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)
    return user

async def verify_password(plain: str, hashed: str) -> bool:
    return pbkdf2_sha256.verify(plain, hashed)

async def set_face_embedding(db: AsyncSession, user: User, embedding: list):
    user.face_embedding = embedding
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user: User, nama: Optional[str] = None):
    if nama is not None:
        user.nama = nama
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
