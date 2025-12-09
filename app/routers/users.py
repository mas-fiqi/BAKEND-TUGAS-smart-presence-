from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import ValidationError
from datetime import datetime, timedelta, date
from jose import jwt, JWTError
from typing import Optional, List
import os
import uuid

from app.schemas.user import UserCreate, UserOut, UserUpdate, Token, TokenData, LoginRequest
from app.schemas.session import AttendanceHistoryOut
from app.database.connection import get_db
from app.services import user_service
from app.face.embedding import embedding_from_upload
from app.config import settings
from app.models import AttendanceRecord, AttendanceSession, ClassRoom

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
    # Save the uploaded image file
    upload_dir = "static/profile_images"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    unique_filename = f"{current_user.id}_{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Generate URL (assuming static files are served from /static/)
    profile_image_url = f"/static/profile_images/{unique_filename}"

    # Process face embedding
    emb = embedding_from_upload(file)
    user = await user_service.set_face_embedding(db, current_user, emb)

    # Update profile image URL
    user.profile_image_url = profile_image_url
    db.add(user)
    await db.commit()
    await db.refresh(user)

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

@router.get("/{user_id}/attendance-history", response_model=List[AttendanceHistoryOut])
async def get_attendance_history(
    user_id: int,
    status: Optional[str] = None,
    class_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get attendance history for a user with optional filters.
    """
    # Base query with joins
    q = select(
        AttendanceRecord.id,
        AttendanceRecord.session_id,
        AttendanceRecord.status,
        AttendanceRecord.method,
        AttendanceRecord.check_in_time,
        AttendanceRecord.timestamp,
        AttendanceSession.tanggal,
        ClassRoom.nama_kelas
    ).join(
        AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
    ).join(
        ClassRoom, AttendanceSession.class_id == ClassRoom.id
    ).where(
        AttendanceRecord.user_id == user_id
    )

    # Apply filters
    if status:
        # Map status: present -> hadir, late -> terlambat, absent -> tidak
        status_map = {"present": "hadir", "late": "terlambat", "absent": "tidak"}
        db_status = status_map.get(status)
        if db_status:
            q = q.where(AttendanceRecord.status == db_status)

    if class_id:
        q = q.where(AttendanceSession.class_id == class_id)

    if from_date:
        try:
            from_d = date.fromisoformat(from_date)
            q = q.where(AttendanceSession.tanggal >= from_d)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from_date format. Use YYYY-MM-DD")

    if to_date:
        try:
            to_d = date.fromisoformat(to_date)
            q = q.where(AttendanceSession.tanggal <= to_d)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to_date format. Use YYYY-MM-DD")

    # Execute query
    result = await db.execute(q)
    rows = result.all()

    # Transform to response format
    history = []
    for row in rows:
        # Map status back to API format
        api_status = row.status
        if row.status == "hadir":
            api_status = "present"
        elif row.status == "terlambat":
            api_status = "late"
        elif row.status == "tidak":
            api_status = "absent"

        check_in_time = row.check_in_time if row.check_in_time else row.timestamp
        history.append({
            "id": row.id,
            "session_id": row.session_id,
            "class_name": row.nama_kelas,
            "date": row.tanggal.isoformat(),
            "status": api_status,
            "method": row.method,
            "check_in_time": check_in_time.isoformat(),
            "session_name": f"Session {row.session_id}",  # Placeholder
            "photo_url": None
        })

    return history


@router.post("/test-endpoint", status_code=status.HTTP_200_OK)
async def test_endpoint():
    return {"message": "Test endpoint in users router works!"}
