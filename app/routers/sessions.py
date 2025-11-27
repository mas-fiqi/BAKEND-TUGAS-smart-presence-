from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.connection import get_db
from app.models import User, AttendanceSession, AttendanceRecord, SessionFallback
from app.schemas import FallbackIn, FallbackOut
from app.routers.deps import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("/{session_id}/attendance-fallback", response_model=FallbackOut)
async def attendance_fallback(
    session_id: int,
    payload: FallbackIn,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):

    # 1) Cari sesi
    sess = await db.get(AttendanceSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    # 2) Validasi PIN
    q = await db.execute(
        select(SessionFallback).where(
            SessionFallback.session_id == session_id,
            SessionFallback.pin == payload.pin
        )
    )
    fallback = q.scalars().first()
    if not fallback:
        raise HTTPException(status_code=401, detail="PIN tidak valid")

    # 3) Buat record attendance
    record = AttendanceRecord(
        session_id=session_id,
        user_id=payload.user_id,
        status="hadir"
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "status": "hadir",
        "user_id": payload.user_id,
        "record_id": record.id
    }
