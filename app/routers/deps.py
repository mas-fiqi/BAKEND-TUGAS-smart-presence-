# app/routers/deps.py
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

# import settings kamu (pastikan app.config.settings ada)
try:
    from app.config import settings
except Exception:
    # fallback nilai default jika config belum diatur
    class _Dummy:
        SECRET_KEY = "changeme"
        ALGORITHM = "HS256"
    settings = _Dummy()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/users/login")

# simple helper: ubah ini supaya ambil user dari DB
def get_user_from_db(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Contoh stub: ganti dengan query DB (SQLAlchemy) untuk ambil user sebenarnya.
    Return dict minimal yang dipakai router (mis. {'id':..., 'nama':..., 'role':...})
    """
    # contoh dummy user untuk development
    if user_id == 1:
        return {"id": 1, "nama": "admin", "email": "admin@local", "role": "admin"}
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Dependency untuk mendapatkan user dari token JWT.
    Mengembalikan dict user. Jika token invalid -> HTTP 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # asumsi payload punya subject 'sub' atau 'user_id'
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            raise credentials_exception
        try:
            user_id = int(user_id)
        except Exception:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_from_db(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
