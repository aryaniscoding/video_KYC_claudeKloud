"""
Run once after first migration to create the default admin user.

Usage: python -m scripts.seed_admin
"""
import asyncio
import uuid
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import get_settings
from app.models.admin import AdminUser

settings = get_settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    engine = create_async_engine(
        settings.supabase_db_url,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
        },
    )
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from sqlalchemy import select
    async with Session() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.email == settings.admin_default_email))
        existing = result.scalar_one_or_none()
        if existing:
            existing.password_hash = pwd_ctx.hash(settings.admin_default_password)
            existing.is_active = True
            await db.commit()
            print(f"Admin updated: {settings.admin_default_email}")
        else:
            admin = AdminUser(
                id=uuid.uuid4(),
                username="admin",
                email=settings.admin_default_email,
                password_hash=pwd_ctx.hash(settings.admin_default_password),
                is_active=True,
            )
            db.add(admin)
            await db.commit()
            print(f"Admin created: {settings.admin_default_email}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
