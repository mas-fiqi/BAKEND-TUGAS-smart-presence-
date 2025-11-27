# models package init
from app.database.connection import Base
# import models so metadata contains tables for create_all
from app.models.user import User  # noqa: F401
from app.models.classroom import ClassRoom  # noqa: F401
from app.models.user_class import UserClass  # noqa: F401
from app.models.attendance_session import AttendanceSession  # noqa: F401
from app.models.attendance_record import AttendanceRecord  # noqa: F401

from app.models.session_fallback import SessionFallback  # noqa: F401
