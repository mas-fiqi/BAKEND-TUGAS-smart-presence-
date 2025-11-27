import asyncio
from passlib.hash import pbkdf2_sha256
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import AsyncSessionLocal, engine, Base
from app.models.user import User
from app.models.classroom import ClassRoom
from app.models.user_class import UserClass

async def init():
    # pastikan tabel ada
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # cek apakah admin sudah ada (gunakan select)
        stmt = select(User).where(User.email == 'admin@local')
        result = await session.execute(stmt)
        existing = result.scalars().first()
        if existing:
            print('Admin sudah ada, skip seed.')
            return

        admin = User(
            nama='Admin',
            email='admin@local',
            password_hash=pbkdf2_sha256.hash('admin123'),
            role='admin'
        )
        session.add(admin)
        await session.flush()  # supaya admin.id tersedia

        kelas = ClassRoom(nama_kelas='Kelas Contoh', kode_kelas='KLS-001')
        session.add(kelas)
        await session.flush()

        uc = UserClass(user_id=admin.id, class_id=kelas.id)
        session.add(uc)

        await session.commit()
        print('Seed selesai: admin + kelas contoh dibuat.')

if __name__ == '__main__':
    asyncio.run(init())
