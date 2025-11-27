# app/services/session_service.py
import math
import secrets
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.attendance_session import AttendanceSession
from app.models.attendance_record import AttendanceRecord
from app.models.session_fallback import SessionFallback
from app.models.user import User

# helper: cosine similarity
def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    # same length? if not, compare up to min length
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    mag_a = math.sqrt(sum(a[i] * a[i] for i in range(n)))
    mag_b = math.sqrt(sum(b[i] * b[i] for i in range(n)))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)

# create session
async def create_session(db: AsyncSession, class_id: int, tanggal, jam_mulai=None, jam_selesai=None) -> AttendanceSession:
    s = AttendanceSession(class_id=class_id, tanggal=tanggal, jam_mulai=jam_mulai, jam_selesai=jam_selesai)
    db.add(s)
    await db.flush()
    # generate fallback pin and save in session_fallback table
    pin = secrets.token_hex(3)  # 6 hex chars
    fb = SessionFallback(session_id=s.id, pin=pin)
    db.add(fb)
    await db.commit()
    await db.refresh(s)
    return s

async def get_session_by_id(db: AsyncSession, session_id: int) -> Optional[AttendanceSession]:
    stmt = select(AttendanceSession).where(AttendanceSession.id == session_id)
    res = await db.execute(stmt)
    return res.scalars().first()

async def list_sessions_by_class(db: AsyncSession, class_id: int):
    stmt = select(AttendanceSession).where(AttendanceSession.class_id == class_id)
    res = await db.execute(stmt)
    return res.scalars().all()

async def start_session(db: AsyncSession, session: AttendanceSession):
    session.jam_mulai = datetime.utcnow().time()
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def end_session(db: AsyncSession, session: AttendanceSession):
    session.jam_selesai = datetime.utcnow().time()
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

# find best matching user by embedding
async def find_best_match(db: AsyncSession, embedding: List[float]) -> (Optional[User], float):
    # fetch users with embeddings
    stmt = select(User).where(User.face_embedding != None)
    res = await db.execute(stmt)
    users = res.scalars().all()
    best_user = None
    best_score = 0.0
    for u in users:
        try:
            db_emb = u.face_embedding
            if not isinstance(db_emb, list):
                continue
            score = cosine_similarity(embedding, db_emb)
            if score > best_score:
                best_score = score
                best_user = u
        except Exception:
            continue
    return best_user, best_score

# attendance by face: threshold default 0.75 (adjustable)
async def mark_attendance_by_face(db: AsyncSession, session: AttendanceSession, embedding: List[float], threshold: float = 0.75):
    user, score = await find_best_match(db, embedding)
    if user and score >= threshold:
        # create record hadir
        rec = AttendanceRecord(session_id=session.id, user_id=user.id, status="hadir")
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        return {"status": "hadir", "user_id": user.id, "score": score}
    else:
        # unknown or low score -> create record 'gagal' or no record (we create gagal)
        rec = AttendanceRecord(session_id=session.id, user_id=None if user is None else user.id, status="gagal")
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
        return {"status": "gagal", "user_id": None if user is None else user.id, "score": score}

# fallback: verify pin
async def fallback_attendance(db: AsyncSession, session: AttendanceSession, user_id: int, pin: str):
    stmt = select(SessionFallback).where(SessionFallback.session_id == session.id)
    res = await db.execute(stmt)
    fb = res.scalars().first()
    if not fb:
        return False
    if fb.pin != pin:
        return False
    # create attendance record hadir
    rec = AttendanceRecord(session_id=session.id, user_id=user_id, status="hadir")
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return True

# user history
async def get_user_history(db: AsyncSession, user_id: int):
    stmt = select(AttendanceRecord).where(AttendanceRecord.user_id == user_id).order_by(AttendanceRecord.timestamp.desc())
    res = await db.execute(stmt)
    return res.scalars().all()
