from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import time, datetime
import logging

from app.database import get_db
from app.models import User, AttendanceSession, AttendanceRecord, SessionFallback
from app.schemas.session import SessionCreate, SessionOut, PinAttendanceRequest, AttendanceRecordOut
from app.schemas.fallback import FallbackIn, FallbackOut, FallbackAttendanceIn, CreateFallbackIn
from app.dependencies import get_current_user

logger = logging.getLogger("sessions-router")

router = APIRouter(tags=["sessions"])

@router.get("/sessions", response_model=List[SessionOut])
async def list_sessions(class_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    # Query with attendance count
    attendance_count = func.count(AttendanceRecord.id).label('attendance_count')
    q = select(
        AttendanceSession,
        attendance_count
    ).outerjoin(
        AttendanceRecord, AttendanceSession.id == AttendanceRecord.session_id
    ).group_by(AttendanceSession.id)

    if class_id is not None:
        q = q.where(AttendanceSession.class_id == class_id)

    result = await db.execute(q)
    rows = result.all()

    sessions_with_count = []
    for row in rows:
        session = row[0]
        count = row[1] or 0
        # Add attendance_count to the session object
        session.attendance_count = count
        sessions_with_count.append(session)

    print("GET /api/sessions?class_id=", class_id, "->", len(sessions_with_count), "items")
    return [SessionOut.from_orm(s) for s in sessions_with_count]

@router.get("/sessions/active", response_model=List[SessionOut])
async def list_active_sessions(db: AsyncSession = Depends(get_db)):
    """
    Get all active sessions. A session is considered active if status = 'active'.
    """
    q = select(AttendanceSession).where(AttendanceSession.status == "active")
    result = await db.execute(q)
    active_sessions = result.scalars().all()
    print("GET /api/sessions/active ->", len(active_sessions), "active sessions")
    return [SessionOut.from_orm(s) for s in active_sessions]


@router.get("/sessions/{session_id}/attendance", response_model=List[AttendanceRecordOut])
async def get_session_attendance(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all attendance records for a specific session.
    """
    q = select(AttendanceRecord, User.nama).join(User, AttendanceRecord.user_id == User.id).where(AttendanceRecord.session_id == session_id)
    result = await db.execute(q)
    records = result.all()

    attendance_list = []
    for record, user_name in records:
        attendance_list.append(AttendanceRecordOut(
            id=record.id,
            session_id=record.session_id,
            user_id=record.user_id,
            status=record.status,
            timestamp=record.timestamp,
            check_in_time=record.check_in_time,
            method=record.method,
            full_name=record.full_name,
            student_number=record.student_number,
            actor_role=record.actor_role,
            user_name=user_name
        ))

    print(f"GET /api/sessions/{session_id}/attendance -> {len(attendance_list)} records")
    return attendance_list


@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role not in ['guru', 'teacher', 'user']:
        raise HTTPException(status_code=403, detail="Hanya guru yang dapat membuat sesi")
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
    payload: FallbackAttendanceIn,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Endpoint fallback absensi yang mendukung PIN dan QR code.
    User diambil dari token Authorization (Bearer).
    """

    # 1) Cari sesi
    sess = await db.get(AttendanceSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session tidak ditemukan")

    # 1.5) Cek apakah session aktif atau bisa diabsen (draft dengan waktu yang sesuai)
    if sess.status != "active" and sess.status != "draft":
        raise HTTPException(status_code=400, detail="Session tidak aktif")

    # 2) Validasi input - harus ada salah satu: PIN atau QR code
    if not payload.pin and not payload.code:
        raise HTTPException(status_code=400, detail="PIN atau QR code harus disediakan")

    if payload.pin and payload.code:
        raise HTTPException(status_code=400, detail="Hanya bisa menggunakan PIN atau QR code, tidak keduanya")

    # 3) Validasi kredensial berdasarkan tipe
    if payload.pin:
        # Validasi PIN
        q = await db.execute(
            select(SessionFallback).where(
                SessionFallback.session_id == session_id,
                SessionFallback.pin == payload.pin
            )
        )
        fallback = q.scalars().first()
        if not fallback:
            raise HTTPException(status_code=401, detail="PIN tidak valid")
    elif payload.code:
        # Validasi QR code
        q = await db.execute(
            select(SessionFallback).where(
                SessionFallback.session_id == session_id,
                SessionFallback.qr_code == payload.code
            )
        )
        fallback = q.scalars().first()
        if not fallback:
            raise HTTPException(status_code=401, detail="QR code tidak valid")

    # 4) Cek apakah user sudah absen untuk session ini
    existing_record_q = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.user_id == current_user.id
        )
    )
    existing_record = existing_record_q.scalars().first()
    if existing_record:
        raise HTTPException(status_code=400, detail="User sudah melakukan absensi untuk sesi ini")

    # 5) Tentukan status berdasarkan waktu
    now = datetime.now()
    status = "hadir"  # present
    if sess.jam_mulai and now.time() > sess.jam_mulai:
        status = "terlambat"  # late

    # 6) Buat record attendance
    record = AttendanceRecord(
        session_id=session_id,
        user_id=current_user.id,
        status=status,
        method="pin" if payload.pin else "qr",
        full_name=payload.full_name,
        student_number=payload.student_number,
        actor_role=payload.actor_role,
        check_in_time=now
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("Fallback attendance recorded: session=%s user=%s method=%s record_id=%s",
                session_id, current_user.id, "PIN" if payload.pin else "QR", record.id)

    return {
        "status": status,
        "user_id": current_user.id,
        "record_id": record.id
    }

@router.post("/sessions/{session_id}/attendance-face", status_code=status.HTTP_200_OK)
async def attendance_face(
    session_id: int,
    file: UploadFile = File(...),
    full_name: Optional[str] = Form(None),
    student_number: Optional[str] = Form(None),
    actor_role: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
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

    # 1.5 Cek apakah session aktif atau bisa diabsen (draft dengan waktu yang sesuai)
    if session_obj.status != "active" and session_obj.status != "draft":
        raise HTTPException(status_code=400, detail="Session tidak aktif")

    # 2. Cek apakah user sudah absen untuk session ini
    existing_record_q = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.user_id == current_user.id
        )
    )
    existing_record = existing_record_q.scalars().first()
    if existing_record:
        raise HTTPException(status_code=400, detail="User sudah melakukan absensi untuk sesi ini")

    # 3. Baca file bytes
    image_bytes = await file.read()

    # 4. TODO: Panggil layanan face recognition jika sudah ada
    #    Misal: user_id, score = verify_face(image_bytes, db, session_obj)
    #    Sekarang buat dummy response agar endpoint tidak 404/500.
    user_id = current_user.id  # Gunakan current_user untuk sementara
    score = None

    # 5. Tentukan status berdasarkan waktu
    now = datetime.now()
    status = "hadir"  # present
    if session_obj.jam_mulai and now.time() > session_obj.jam_mulai:
        status = "terlambat"  # late

    # 6. Simpan AttendanceRecord
    record = AttendanceRecord(
        session_id=session_id,
        user_id=user_id,
        status=status,
        method="face",
        full_name=full_name,
        student_number=student_number,
        actor_role=actor_role,
        check_in_time=now
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    print(f"[DEBUG] AttendanceRecord created: user_id={user_id}, session_id={session_id}, method=face, record_id={record.id}")

    return {
        "status": status,
        "user_id": user_id,
        "score": score,
        "record_id": record.id,
        "user_info": {
            "nama": current_user.nama,
            "nim": student_number or "N/A"
        }
    }

@router.post("/sessions/{session_id}/start", status_code=status.HTTP_200_OK)
async def start_session(session_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role not in ['guru', 'teacher', 'user']:
        raise HTTPException(status_code=403, detail="Hanya guru yang dapat memulai sesi")
    """
    Endpoint ketika user menekan tombol START pada sesi absensi.
    Mengubah status sesi menjadi 'active' dan set waktu mulai jika ada kolomnya.
    """
    logger.info("POST /api/sessions/%s/start", session_id)
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set status menjadi active (jam_mulai sudah di-set saat create session)
    session_obj.status = "active"

    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)
    logger.info("Session %s started", session_id)
    return {"status": "ok", "message": "Session started", "session_id": session_id}

@router.post("/sessions/{session_id}/end", status_code=status.HTTP_200_OK)
async def end_session(session_id: int, db: AsyncSession = Depends(get_db), current_user = Depends(get_current_user)):
    if current_user.role not in ['guru', 'teacher', 'user']:
        raise HTTPException(status_code=403, detail="Hanya guru yang dapat mengakhiri sesi")
    """
    Endpoint untuk mengakhiri sesi absensi (STOP).
    Mengubah status sesi menjadi 'ended'.
    """
    logger.info("POST /api/sessions/%s/end", session_id)
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Set jam_selesai dengan waktu sekarang dan status menjadi ended
    now = datetime.now()
    session_obj.jam_selesai = now.time()
    session_obj.status = "ended"

    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)
    logger.info("Session %s ended", session_id)
    return {"status": "ok", "message": "Session ended", "session_id": session_id}

@router.post("/sessions/{session_id}/fallback", response_model=dict)
async def create_session_fallback(
    session_id: int,
    payload: CreateFallbackIn,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create fallback credentials (PIN and/or QR code) for a session.
    This endpoint allows setting up authentication methods for attendance fallback.
    """
    # Check if session exists
    session_obj = await db.get(AttendanceSession, session_id)
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if fallback already exists
    existing_q = await db.execute(
        select(SessionFallback).where(SessionFallback.session_id == session_id)
    )
    existing = existing_q.scalars().first()

    if existing:
        # Update existing fallback
        if payload.pin is not None:
            existing.pin = payload.pin
        if payload.qr_code is not None:
            existing.qr_code = payload.qr_code
        db.add(existing)
    else:
        # Create new fallback
        if not payload.pin and not payload.qr_code:
            raise HTTPException(status_code=400, detail="PIN or QR code must be provided")

        fallback = SessionFallback(
            session_id=session_id,
            pin=payload.pin,
            qr_code=payload.qr_code
        )
        db.add(fallback)

    await db.commit()

    return {
        "message": "Session fallback credentials updated successfully",
        "session_id": session_id,
        "has_pin": payload.pin is not None,
        "has_qr_code": payload.qr_code is not None
    }

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

    # 1.5. Cek apakah session aktif atau bisa diabsen (draft dengan waktu yang sesuai)
    if session_obj.status != "active" and session_obj.status != "draft":
        raise HTTPException(status_code=400, detail="Session tidak aktif")

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

    # 4. Tentukan status berdasarkan waktu
    now = datetime.now()
    status = "hadir"  # present
    if session_obj.jam_mulai and now.time() > session_obj.jam_mulai:
        status = "terlambat"  # late

    # 5. Buat record attendance baru
    record = AttendanceRecord(
        session_id=session_id,
        user_id=current_user.id,
        status=status,
        method="pin",
        full_name=payload.full_name,
        student_number=payload.student_number,
        actor_role=payload.actor_role,
        check_in_time=now
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info("Attendance recorded: session=%s user=%s record_id=%s",
                session_id, current_user.id, record.id)

    return {
        "status": status,
        "message": "Attendance marked successfully",
        "session_id": session_id,
        "user_id": current_user.id,
        "record_id": record.id
    }
