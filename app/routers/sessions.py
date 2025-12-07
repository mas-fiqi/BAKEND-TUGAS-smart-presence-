from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import time, datetime
import logging

from app.database.connection import get_db
from app.models import User, AttendanceSession, AttendanceRecord, SessionFallback
from app.schemas.session import SessionCreate, SessionOut, PinAttendanceRequest
from app.schemas.fallback import FallbackIn, FallbackOut
from app.routers.deps import get_current_user

logger = logging.getLogger("sessions-router")

router = APIRouter(tags=["sessions"])

@router.get("/sessions", response_model=List[SessionOut])
async def list_sessions(class_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    q = select(AttendanceSession)
    if class_id is not None:
        q = q.where(AttendanceSession.class_id == class_id)
    result = await db.execute(q)
    sessions = result.scalars().all()
    print("GET /api/sessions?class_id=", class_id, "->", len(sessions), "items")
    return [SessionOut.from_orm(s) for s in sessions]

@router.get("/sessions/active", response_model=List[SessionOut])
async def list_active_sessions(db: AsyncSession = Depends(get_db)):
    """
    Get all active sessions. A session is considered active if:
    - jam_mulai is set and jam_selesai is null (started but not ended)
    """
    q = select(AttendanceSession).where(
        AttendanceSession.jam_mulai.isnot(None),
        AttendanceSession.jam_selesai.is_(None)
    )
    result = await db.execute(q)
    active_sessions = result.scalars().all()
    print("GET /api/sessions/active ->", len(active_sessions), "active sessions")
    return [SessionOut.from_orm(s) for s in active_sessions]


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    print("POST /api/sessions payload:", payload)

    # Konversi string jam "HH:MM" menjadi datetime.time
    def parse_time_str(t: str) -> time:
        if t is None:
            return None
        parts = t.split(":")
        if len(parts) < 2:
            raise ValueError(f"Format jam tidak valid: {t}")
        h = int(parts[0])
        m = int(parts[1])
        return time(hour=h, minute=m)

    jam_mulai_py = parse_time_str(payload.jam_mulai)
    jam_selesai_py = parse_time_str(payload.jam_selesai)

    session_obj = AttendanceSession(
        class_id=payload.class_id,
        tanggal=payload.tanggal,
        jam_mulai=jam_mulai_py,
        jam_selesai=jam_selesai_py
    )
    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)
    print("Created session:", session_obj.id, session_obj.class_id)
    return SessionOut.from_orm(session_obj)

@router.post("/sessions/{session_id}/attendance-fallback", response_model=FallbackOut)
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

@router.post("/sessions/{session_id}/attendance-face", status_code=status.HTTP_200_OK)
async def attendance_face(
    session_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint yang dipanggil ketika Flutter upload foto wajah untuk absensi.
    Path yang diharapkan frontend: POST /api/sessions/{session_id}/attendance-face
    Content-Type: multipart/form-data, field name: file
    """
    # 1. Cek apakah session ada
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Baca file bytes
    image_bytes = await file.read()

    # 3. TODO: Panggil layanan face recognition jika sudah ada
    #    Misal: user_id, score = verify_face(image_bytes, db, session_obj)
    #    Sekarang buat dummy response agar endpoint tidak 404/500.
    user_id = None
    score = None

    # 4. TODO: Simpan AttendanceRecord jika diperlukan
    #    Misal:
    #    record = AttendanceRecord(
    #        session_id=session_id,
    #        user_id=user_id,
    #        status="present",
    #        confidence=score,
    #    )
    #    db.add(record)
    #    db.commit()
    #    db.refresh(record)

    return {
        "status": "ok",
        "session_id": session_id,
        "message": "Face attendance endpoint hit successfully (dummy implementation)."
    }

@router.post("/sessions/{session_id}/start", status_code=status.HTTP_200_OK)
async def start_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint ketika user menekan tombol START pada sesi absensi.
    Mengubah status sesi menjadi 'ongoing' dan set waktu mulai jika ada kolomnya.
    """
    logger.info("POST /api/sessions/%s/start", session_id)
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set jam_mulai dengan waktu sekarang
    now = datetime.now()
    session_obj.jam_mulai = now.time()

    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)
    logger.info("Session %s started", session_id)
    return {"status": "ok", "message": "Session started", "session_id": session_id}

@router.post("/sessions/{session_id}/end", status_code=status.HTTP_200_OK)
async def end_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint untuk mengakhiri sesi absensi (STOP).
    """
    logger.info("POST /api/sessions/%s/end", session_id)
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set jam_selesai dengan waktu sekarang
    now = datetime.now()
    session_obj.jam_selesai = now.time()

    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)
    logger.info("Session %s ended", session_id)
    return {"status": "ok", "message": "Session ended", "session_id": session_id}

@router.post("/sessions/{session_id}/attendance-pin", status_code=status.HTTP_200_OK)
async def attendance_pin(
    session_id: int,
    payload: PinAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Endpoint untuk absensi menggunakan PIN.
    User yang sedang login mengirim PIN untuk validasi kehadiran.
    """
    logger.info("POST /api/sessions/%s/attendance-pin user_id=%s", session_id, current_user.id)

    # 1. Cek apakah session ada
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Validasi PIN untuk session ini
    q = await db.execute(
        select(SessionFallback).where(
            SessionFallback.session_id == session_id,
            SessionFallback.pin == payload.pin
        )
    )
    fallback = q.scalars().first()
    if not fallback:
        raise HTTPException(status_code=401, detail="Invalid PIN for this session")

    # 3. Cek apakah user sudah absen untuk session ini
    existing_record_q = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.user_id == current_user.id
        )
    )
    existing_record = existing_record_q.scalars().first()
    if existing_record:
        raise HTTPException(status_code=400, detail="User already marked attendance for this session")

    # 4. Buat record attendance baru
    record = AttendanceRecord(
        session_id=session_id,
        user_id=current_user.id,
        status="hadir"
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("Attendance recorded: session=%s user=%s record_id=%s",
                session_id, current_user.id, record.id)

    return {
        "status": "success",
        "message": "Attendance marked successfully",
        "session_id": session_id,
        "user_id": current_user.id,
        "record_id": record.id
    }
