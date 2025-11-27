from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Optional

from app.schemas.user import UserCreate, UserOut, UserUpdate, Token, TokenData, LoginRequest
from app.database.connection import get_db
from app.services import user_service
from app.face.embedding import embedding_from_upload
from app.config import settings

router = APIRouter()

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user_from_header(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("user_id"))
    except (JWTError, ValidationError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = await user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await user_service.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    user = await user_service.create_user(
        db,
        nama=payload.nama,
        email=payload.email,
        password=payload.password
    )
    return UserOut.from_orm(user)


@router.post("/login", response_model=Token)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login menggunakan email + password saja"""
    user = await user_service.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=400, detail="Email/password salah")

    valid = await user_service.verify_password(payload.password, user.password_hash)
    if not valid:
        raise HTTPException(status_code=400, detail="Email/password salah")

    access_token = await create_access_token({"user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/upload-face", response_model=UserOut)
async def upload_face(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db)
):
    emb = embedding_from_upload(file)
    user = await user_service.set_face_embedding(db, current_user, emb)
    return UserOut.from_orm(user)


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user_from_header)):
    return UserOut.from_orm(current_user)


@router.put("/me", response_model=UserOut)
async def update_me(
    payload: UserUpdate,
    current_user=Depends(get_current_user_from_header),
    db: AsyncSession = Depends(get_db)
):
    user = await user_service.update_user(db, current_user, nama=payload.nama)
    return UserOut.from_orm(user)
