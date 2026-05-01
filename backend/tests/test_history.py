"""Tests for prior application history check — 7 ML features + velocity flags."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio

from app.models import Customer, PriorApplication
from app.services.history_service import run_history_check


@pytest_asyncio.fixture
async def clean_customer(db):
    c = Customer(
        id=uuid.uuid4(), name="Test User", email="t@t.com",
        phone_hash="hash1", phone_last4="0001",
        product_code="PL_STANDARD", max_loan_amount=500000,
    )
    db.add(c)
    await db.commit()
    return c


@pytest_asyncio.fixture
async def customer_with_history(db, clean_customer):
    now = datetime.now(timezone.utc)
    apps = [
        PriorApplication(
            id=uuid.uuid4(), customer_id=clean_customer.id,
            phone_hash=clean_customer.phone_hash,
            outcome="withdrawn", risk_band="MEDIUM_LOW",
            loan_performance="unknown",
            applied_at=now - timedelta(days=180),
        ),
    ]
    for a in apps:
        db.add(a)
    await db.commit()
    return clean_customer


@pytest_asyncio.fixture
async def approved_good_customer(db, clean_customer):
    """Customer with approved + good repayment history — qualifies for fast-track."""
    now = datetime.now(timezone.utc)
    db.add(PriorApplication(
        id=uuid.uuid4(), customer_id=clean_customer.id,
        phone_hash=clean_customer.phone_hash,
        outcome="approved", risk_band="LOW",
        loan_performance="good",
        applied_at=now - timedelta(days=365),
    ))
    await db.commit()
    return clean_customer


@pytest_asyncio.fixture
async def velocity_fraud_customer(db, clean_customer):
    """Customer with 4 applications in 30 days — soft velocity flag."""
    now = datetime.now(timezone.utc)
    for i in range(4):
        db.add(PriorApplication(
            id=uuid.uuid4(), customer_id=clean_customer.id,
            phone_hash=clean_customer.phone_hash,
            outcome="declined", risk_band=None,
            loan_performance="unknown",
            applied_at=now - timedelta(days=i),
        ))
    await db.commit()
    return clean_customer


@pytest_asyncio.fixture
async def hard_pause_customer(db, clean_customer):
    """Customer with 7 applications in 7 days — hard pause."""
    now = datetime.now(timezone.utc)
    for i in range(7):
        db.add(PriorApplication(
            id=uuid.uuid4(), customer_id=clean_customer.id,
            phone_hash=clean_customer.phone_hash,
            outcome="declined", risk_band=None,
            loan_performance="unknown",
            applied_at=now - timedelta(hours=i * 12),
        ))
    await db.commit()
    return clean_customer


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_first_time_applicant(db, clean_customer):
    result = await run_history_check(clean_customer, db)
    assert result["prior_applications_count"] == 0
    assert result["prior_rejections_count"] == 0
    assert result["days_since_last_app"] == 999
    assert result["last_outcome_encoded"] == 0
    assert result["application_velocity_30d"] == 0
    assert result["velocity_fraud_flag"] is False
    assert result["hard_pause"] is False
    assert result["is_fast_track"] is False


@pytest.mark.asyncio
async def test_withdrawn_history(db, customer_with_history):
    result = await run_history_check(customer_with_history, db)
    assert result["prior_applications_count"] == 1
    assert result["prior_rejections_count"] == 0
    assert result["days_since_last_app"] == pytest.approx(180, abs=2)
    assert result["last_outcome_encoded"] == 3   # withdrawn
    assert result["is_fast_track"] is False


@pytest.mark.asyncio
async def test_fast_track_approved_good(db, approved_good_customer):
    result = await run_history_check(approved_good_customer, db)
    assert result["is_fast_track"] is True
    assert result["last_outcome_encoded"] == 1   # approved
    assert result["prior_loan_performance_encoded"] == 1   # good
    assert result["pre_fill_data"] is not None
    assert result["pre_fill_data"]["full_name"] == approved_good_customer.name


@pytest.mark.asyncio
async def test_velocity_soft_flag(db, velocity_fraud_customer):
    result = await run_history_check(velocity_fraud_customer, db)
    assert result["application_velocity_30d"] == 4
    assert result["velocity_fraud_flag"] is True
    assert result["hard_pause"] is False


@pytest.mark.asyncio
async def test_velocity_hard_pause(db, hard_pause_customer):
    result = await run_history_check(hard_pause_customer, db)
    assert result["hard_pause"] is True
    assert result["application_velocity_30d"] >= 7


@pytest.mark.asyncio
async def test_7_feature_keys_always_present(db, clean_customer):
    result = await run_history_check(clean_customer, db)
    required_keys = [
        "prior_applications_count", "prior_rejections_count", "days_since_last_app",
        "last_outcome_encoded", "prior_risk_band_encoded",
        "prior_loan_performance_encoded", "application_velocity_30d",
    ]
    for key in required_keys:
        assert key in result, f"Missing feature: {key}"
