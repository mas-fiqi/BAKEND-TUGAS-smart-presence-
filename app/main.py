from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import api_router
from app.database.connection import engine, Base
import asyncio
import os

app = FastAPI(title="Smart Presence API")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# include router (meskipun kosong sekarang)
app.include_router(api_router, prefix="/api")

@app.on_event("startup")
async def on_startup():
    # Opsional: buat tabel otomatis (hanya untuk dev; gunakan alembic untuk production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Startup complete - DB tables created (if not exist).")

@app.get("/")
async def root():
    return {"message": "Smart Presence API — backend siap."}
