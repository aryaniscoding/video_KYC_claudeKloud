"""
Pytest fixtures shared across all tests.
Uses an in-memory SQLite engine so tests run without a real Supabase connection.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.base import Base
from app.models import (
    AdminUser, Customer, Session, SessionStatus,
    Application, Decision, AuditLog, PriorApplication,
)

# ── In-memory SQLite engine for tests ─────────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_test_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    async with TestSession() as session:
        yield session
        await session.rollback()


# ── Override app dependencies ──────────────────────────────────────────────────

@pytest.fixture
def app():
    """FastAPI app with DB dependency overridden to use test SQLite."""
    from app.main import app as _app
    from app.database import get_db

    async def override_get_db():
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    _app.dependency_overrides[get_db] = override_get_db
    yield _app
    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Common test data (Ramesh Kumar from blueprint §13) ─────────────────────────

RAMESH = {
    "name": "Ramesh Kumar",
    "email": "ramesh.kumar@example.com",
    "phone": "9876543210",
    "phone_last4": "3210",
    "credit_score": 742,
    "dpd_12m": 0,
    "dpd_24m": 0,
    "active_loans_count": 1,
    "total_outstanding_inr": 120000.0,
    "monthly_income": 58000.0,
    "employment_type": "salaried",
    "employer_name": "TCS",
    "job_tenure_years": 6.0,
    "existing_emi_monthly": 8000.0,
    "requested_amount": 400000.0,
    "preferred_tenure_months": 24,
    "loan_purpose": "personal",
    "city": "Pune",
    "state": "Maharashtra",
    "pincode": "411027",
}

RAMESH_35_FEATURES = {
    "credit_score": 742.0,
    "dpd_12m": 0.0,
    "dpd_24m": 0.0,
    "active_loans_count": 1.0,
    "total_outstanding_inr": 120000.0,
    "monthly_income": 58000.0,
    "employment_type": 1.0,
    "employer_tier": 3.0,
    "job_tenure_years": 6.0,
    "requested_amount": 400000.0,
    "loan_to_income_ratio": round(400000 / 58000, 4),
    "preferred_tenure_months": 24.0,
    "loan_purpose_encoded": 9.0,
    "existing_emi_monthly": 8000.0,
    "total_obligations": 8000.0,
    "foir_ratio": round(8000 / 58000, 4),
    "debt_to_income": round(8000 / 58000, 4),
    "geo_risk_score": 0.08,
    "ip_risk_score": 0.05,
    "device_risk_score": 0.03,
    "liveness_score": 0.92,
    "age_consistency_score": 0.89,
    "face_confidence_score": 0.95,
    "avg_response_latency_ms": 3200.0,
    "hesitation_count": 1.0,
    "question_retry_count": 0.0,
    "extraction_confidence_avg": 0.944,
    "inconsistency_score": 0.04,
    "consent_confidence": 0.97,
    "prior_applications_count": 1.0,
    "prior_rejections_count": 0.0,
    "days_since_last_app": 180.0,
    "last_outcome_encoded": 3.0,
    "prior_risk_band_encoded": 0.0,
    "prior_loan_performance_encoded": 0.0,
    "application_velocity_30d": 0.0,
}


@pytest_asyncio.fixture
async def ramesh_customer(db):
    import hashlib
    phone_hash = hashlib.sha256("9876543210".encode()).hexdigest()
    customer = Customer(
        id=uuid.uuid4(),
        name=RAMESH["name"],
        email=RAMESH["email"],
        phone_hash=phone_hash,
        phone_last4=RAMESH["phone_last4"],
        product_code="PL_STANDARD",
        max_loan_amount=500000.0,
        credit_score=RAMESH["credit_score"],
        dpd_12m=RAMESH["dpd_12m"],
        dpd_24m=RAMESH["dpd_24m"],
        active_loans_count=RAMESH["active_loans_count"],
        total_outstanding_inr=RAMESH["total_outstanding_inr"],
    )
    db.add(customer)
    await db.commit()
    return customer


@pytest_asyncio.fixture
async def ramesh_session(db, ramesh_customer):
    from app.services.jwt_service import create_session_token
    token, payload = create_session_token(
        customer_id=ramesh_customer.id,
        phone_hash=ramesh_customer.phone_hash,
        product_code="PL_STANDARD",
        max_amount=500000.0,
    )
    session = Session(
        id=uuid.uuid4(),
        customer_id=ramesh_customer.id,
        token_jti=payload["jti"],
        policy_ver="v1.0",
        product_code="PL_STANDARD",
        max_amount=500000.0,
        token_issued_at=datetime.now(timezone.utc),
        token_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        status=SessionStatus.PENDING,
        geo_risk_score=0.08,
        ip_risk_score=0.05,
        device_risk_score=0.03,
        liveness_score=0.92,
        age_consistency_score=0.89,
        face_confidence=0.95,
        consent_confidence=0.97,
        avg_response_latency_ms=3200.0,
        hesitation_count=1,
        question_retry_count=0,
    )
    db.add(session)
    await db.commit()
    return session, token
