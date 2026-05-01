"""
Prior Application History Check — Phase 2 of the blueprint.

Returns 7 ML features + velocity fraud flag + fast-track signal.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Customer, PriorApplication


_OUTCOME_MAP = {"approved": 1, "declined": 2, "withdrawn": 3, "hitl": 4}
_RISK_BAND_MAP = {"LOW": 1, "MEDIUM_LOW": 2, "MEDIUM_HIGH": 3, "HIGH": 4, "VERY_HIGH": 5}
_PERFORMANCE_MAP = {"good": 1, "bad": 2, "unknown": 0}


async def run_history_check(customer: Customer, db: AsyncSession) -> dict:
    """
    Returns a dict with:
      - 7 ML features (keyed exactly as in features.json)
      - velocity_fraud_flag (bool)
      - hard_pause (bool) — velocity >= 7 in 7d
      - is_fast_track (bool)
      - pre_fill_data (dict | None)
    """
    result = await db.execute(
        select(PriorApplication)
        .where(PriorApplication.customer_id == customer.id)
        .order_by(PriorApplication.applied_at.desc())
    )
    prior_apps = result.scalars().all()

    now = datetime.now(timezone.utc)
    window_30d = now - timedelta(days=30)
    window_7d = now - timedelta(days=7)

    apps_30d = [a for a in prior_apps if a.applied_at >= window_30d]
    apps_7d = [a for a in prior_apps if a.applied_at >= window_7d]

    prior_applications_count = len(prior_apps)
    prior_rejections_count = sum(1 for a in prior_apps if a.outcome == "declined")
    application_velocity_30d = len(apps_30d)

    if prior_apps:
        last_app = prior_apps[0]
        days_since_last_app = (now - last_app.applied_at).days
        last_outcome_encoded = _OUTCOME_MAP.get(last_app.outcome, 0)
        prior_risk_band_encoded = _RISK_BAND_MAP.get(last_app.risk_band, 0) if last_app.risk_band else 0
        prior_loan_performance_encoded = _PERFORMANCE_MAP.get(last_app.loan_performance, 0)
    else:
        days_since_last_app = 999   # first-time applicant sentinel
        last_outcome_encoded = 0
        prior_risk_band_encoded = 0
        prior_loan_performance_encoded = 0

    velocity_fraud_flag = application_velocity_30d >= 3
    hard_pause = len(apps_7d) >= 7

    # Fast-track: last outcome approved + clean performance + no recent rejections
    is_fast_track = (
        prior_applications_count > 0
        and last_outcome_encoded == _OUTCOME_MAP["approved"]
        and prior_loan_performance_encoded == _PERFORMANCE_MAP["good"]
        and prior_rejections_count == 0
    )

    pre_fill_data = None
    if is_fast_track:
        pre_fill_data = {
            "full_name": customer.name,
        }

    return {
        # ── 7 ML features (exact names) ──────────────────────────────────────
        "prior_applications_count": prior_applications_count,
        "prior_rejections_count": prior_rejections_count,
        "days_since_last_app": days_since_last_app,
        "last_outcome_encoded": last_outcome_encoded,
        "prior_risk_band_encoded": prior_risk_band_encoded,
        "prior_loan_performance_encoded": prior_loan_performance_encoded,
        "application_velocity_30d": application_velocity_30d,
        # ── Control flags ────────────────────────────────────────────────────
        "velocity_fraud_flag": velocity_fraud_flag,
        "hard_pause": hard_pause,
        "is_fast_track": is_fast_track,
        "pre_fill_data": pre_fill_data,
    }
