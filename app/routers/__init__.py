from fastapi import APIRouter
from app.routers import users as users_router
from app.routers import classes as classes_router
from app.routers import sessions as sessions_router

api_router = APIRouter()

api_router.include_router(users_router.router, prefix="/users", tags=["users"])
api_router.include_router(classes_router.router, prefix="/classes", tags=["classes"])
api_router.include_router(sessions_router.router, prefix="/sessions", tags=["sessions"])
 