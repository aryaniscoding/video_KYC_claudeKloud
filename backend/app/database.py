import uuid
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from supabase import create_client, Client
from app.config import get_settings

settings = get_settings()

# ── SQLAlchemy async engine (Supabase PostgreSQL via PgBouncer pooler) ────────
engine = create_async_engine(
    settings.supabase_db_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    # PgBouncer transaction mode — no prepared statements
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency — auto-commits on success, rolls back on exception."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Supabase client (storage + realtime helpers) ──────────────────────────────
def get_supabase() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)
