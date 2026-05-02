"""
Customer-facing session API.

GET  /session/{token}           — validate JWT, run pre-checks, return session config
GET  /session/{session_id}/offer — get offer after decision
GET  /offers/{offer_ref_id}/download — redirect to pre-signed PDF URL
"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Customer, Session, SessionStatus, Decision, OfferPDF
from app.schemas.session import (
    PreSessionRequest, SessionInitResponse, PreSessionScores,
    OfferResponse, EMIOption, DownloadURLResponse,
)
from app.services.jwt_service import decode_session_token, TokenExpiredError, TokenTamperedError
from app.services.history_service import run_history_check
from app.services.scoring_service import compute_pre_session_scores
from app.services.livekit_service import create_room_and_token

router = APIRouter(tags=["session"])
settings = get_settings()


def _get_client_ip(request: Request) -> str:
    """Real client IP — ProxyHeadersMiddleware already rewrites request.client,
    but we also check X-Forwarded-For directly as a belt-and-suspenders fallback."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


# ── GET /session/{token} ──────────────────────────────────────────────────────

@router.get("/session/{token}", response_model=SessionInitResponse)
async def init_session(
    token: str,
    request: Request,
    body: PreSessionRequest = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate JWT
    try:
        payload = decode_session_token(token)
    except TokenExpiredError:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="session_expired")
    except TokenTamperedError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session_invalid")

    # 2. Lookup session in DB
    result = await db.execute(select(Session).where(Session.token_jti == payload["jti"]))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session record not found")

    # 3. Reject already-used terminal states
    terminal = {SessionStatus.APPROVED, SessionStatus.DECLINED, SessionStatus.EXPIRED}
    if session.status in terminal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"session_{session.status.value}",
        )

    # 4. Customer
    cust_result = await db.execute(select(Customer).where(Customer.id == session.customer_id))
    customer = cust_result.scalar_one()

    # 5. Store incoming location + device fingerprint
    client_ip = _get_client_ip(request)
    session.ip_address = client_ip
    if body.latitude is not None:
        session.latitude = body.latitude
        session.longitude = body.longitude
    if body.device_fingerprint:
        session.device_fingerprint = body.device_fingerprint

    # 6. Prior application history check (7 ML features + fast-track flag)
    history = await run_history_check(customer, db)
    session.velocity_fraud_flag = history["velocity_fraud_flag"]
    session.is_fast_track = history["is_fast_track"]

    # Velocity >= 7 in 7d → HITL pause before session starts
    if history.get("hard_pause"):
        session.status = SessionStatus.HITL
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="velocity_fraud_pause",
        )

    # 7. Pre-session risk scores
    scores_raw = await compute_pre_session_scores(
        latitude=body.latitude,
        longitude=body.longitude,
        ip_address=client_ip,
        pincode=None,   # extracted later in Q&A
        device_fingerprint=body.device_fingerprint,
    )
    session.geo_risk_score = scores_raw["geo_risk_score"]
    session.ip_risk_score = scores_raw["ip_risk_score"]
    session.device_risk_score = scores_raw["device_risk_score"]
    session.ip_city = scores_raw.get("ip_city")
    session.ip_state = scores_raw.get("ip_state")
    session.ip_zip = scores_raw.get("ip_zip")

    # If browser GPS was not granted, fall back to IP-derived coordinates
    if session.latitude is None and scores_raw.get("ip_latitude") is not None:
        session.latitude = scores_raw["ip_latitude"]
        session.longitude = scores_raw["ip_longitude"]

    scores = PreSessionScores(**scores_raw)
    if scores.hard_stop:
        session.status = SessionStatus.DECLINED
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=scores.hard_stop_reason or "hard_stop",
        )

    # 8. LiveKit room + customer token
    room_name, livekit_token = await create_room_and_token(str(session.token_jti), str(customer.id))
    session.livekit_room_name = room_name
    session.status = SessionStatus.STARTED
    session.langgraph_thread_id = str(session.token_jti)

    await db.commit()

    pre_fill = None
    if history["is_fast_track"]:
        pre_fill = history.get("pre_fill_data")

    return SessionInitResponse(
        session_id=session.token_jti,
        token=token,
        customer_id=customer.id,
        customer_name=customer.name,
        product_code=session.product_code,
        is_fast_track=session.is_fast_track,
        pre_fill=pre_fill,
        scores=scores,
        livekit_token=livekit_token,
        livekit_url=settings.livekit_host.replace("http://", "ws://").replace("https://", "wss://"),
        policy_ver=session.policy_ver,
    )


# ── POST /session/{session_id}/pan ───────────────────────────────────────────

class PanSubmitRequest(BaseModel):
    pan_number: str

@router.post("/session/{session_id}/pan", status_code=200)
async def submit_pan(session_id: str, body: PanSubmitRequest, db: AsyncSession = Depends(get_db)):
    pan = body.pan_number.strip().upper()
    if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan):
        raise HTTPException(status_code=422, detail="Invalid PAN format. Must be 5 letters, 4 digits, 1 letter.")

    result = await db.execute(select(Session).where(Session.token_jti == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cust_result = await db.execute(select(Customer).where(Customer.id == session.customer_id))
    customer = cust_result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.pan_number = pan
    await db.commit()
    return {"success": True}


# ── GET /session/{session_id}/offer ──────────────────────────────────────────

@router.get("/session/{session_id}/offer", response_model=OfferResponse)
async def get_offer(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.token_jti == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.PROCESSING:
        raise HTTPException(status_code=202, detail="processing")

    if session.status == SessionStatus.DECLINED:
        dec_result = await db.execute(select(Decision).where(Decision.session_id == session.id))
        decision = dec_result.scalar_one_or_none()
        # Build human-readable decline reason
        if decision and not decision.hard_rules_passed and decision.failing_rule_reason:
            decline_reason = decision.failing_rule_reason
        elif decision and decision.risk_band in ("HIGH", "VERY_HIGH"):
            pd_pct = f"{decision.pd_score * 100:.1f}%" if decision.pd_score else "high"
            decline_reason = (
                f"Our risk model assessed a {pd_pct} probability of default "
                f"(risk band: {decision.risk_band}). This exceeds our current approval threshold."
            )
        else:
            decline_reason = "Based on the information provided, you do not meet our current eligibility criteria."
        return OfferResponse(
            eligible=False,
            decline_reason=decline_reason,
            decline_tips=_get_decline_tips(decision),
            failing_rule=decision.failing_rule if decision else None,
            risk_band=decision.risk_band if decision else None,
            pd_score=decision.pd_score if decision else None,
            risk_factors=_shap_to_plain_english(
                decision.top_positive_features if decision else None, mode="risk"
            ),
        )

    if session.status == SessionStatus.HITL:
        return OfferResponse(
            eligible=False,
            under_review=True,
            decline_reason="Your application has been flagged for manual review. Our team will contact you within 24 hours.",
        )

    if session.status != SessionStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Offer not yet ready")

    dec_result = await db.execute(select(Decision).where(Decision.session_id == session.id))
    decision = dec_result.scalar_one_or_none()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    emi_options = [EMIOption(**opt) for opt in (decision.emi_options or [])]

    return OfferResponse(
        eligible=True,
        approved_amount=decision.approved_amount,
        interest_rate_pct=decision.interest_rate,
        recommended_tenure_months=decision.recommended_tenure_months,
        emi_options=emi_options,
        processing_fee_pct=decision.processing_fee_pct,
        offer_ref_id=decision.offer_ref_id,
        offer_valid_until=decision.offer_valid_until,
        approval_reasons=_shap_to_plain_english(decision.top_negative_features, mode="approval"),
        risk_factors=_shap_to_plain_english(decision.top_positive_features, mode="risk"),
        risk_band=decision.risk_band,
        pd_score=decision.pd_score,
    )


# ── GET /offers/{offer_ref_id}/download ───────────────────────────────────────

@router.get("/offers/{offer_ref_id}/download", response_model=DownloadURLResponse)
async def download_offer(offer_ref_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(OfferPDF).where(OfferPDF.offer_ref_id == offer_ref_id)
    )
    pdf = result.scalar_one_or_none()
    if not pdf:
        raise HTTPException(status_code=404, detail="Offer PDF not found")

    now = datetime.now(timezone.utc)
    if pdf.download_expires_at and pdf.download_expires_at < now:
        raise HTTPException(status_code=410, detail="Download link expired")

    return DownloadURLResponse(download_url=pdf.download_url, expires_at=pdf.download_expires_at)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _shap_to_plain_english(top_features: list | None, mode: str = "approval") -> list[str]:
    if not top_features:
        return []
    approval_map = {
        "credit_score": "Strong credit history",
        "monthly_income": "Healthy monthly income",
        "foir_ratio": "Low existing debt obligations",
        "post_loan_foir": "Affordable EMI-to-income ratio",
        "job_tenure_years": "Stable employment tenure",
        "liveness_score": "Identity successfully verified",
        "extraction_confidence_avg": "Clear and consistent application",
        "prior_loan_performance_encoded": "Good past repayment history",
        "consent_confidence": "Clear consent given",
        "age_consistency_score": "Age verified consistently",
    }
    risk_map = {
        "credit_score": "Low credit score",
        "monthly_income": "Insufficient income for requested amount",
        "foir_ratio": "High existing debt obligations",
        "post_loan_foir": "Total EMIs would exceed 50% of income",
        "dpd_12m": "Recent payment defaults (last 12 months)",
        "dpd_24m": "Payment defaults in last 24 months",
        "job_tenure_years": "Short employment history",
        "active_loans_count": "Too many active loans",
        "total_outstanding_inr": "High outstanding loan balance",
        "geo_risk_score": "Location mismatch or high-risk area",
        "ip_risk_score": "Suspicious network detected",
        "inconsistency_score": "Inconsistencies found in stated information",
        "prior_rejections_count": "Multiple prior loan rejections",
        "application_velocity_30d": "Multiple recent loan applications",
    }
    label_map = risk_map if mode == "risk" else approval_map
    return [label_map.get(f, f.replace("_", " ").title()) for f in top_features[:3]]


def _get_decline_tips(decision) -> list[str]:
    if not decision:
        return ["Please contact our helpline for assistance."]
    # ML-based decline (no failing hard rule)
    if decision.hard_rules_passed and decision.risk_band in ("HIGH", "VERY_HIGH"):
        tips = ["Improve your CIBIL score by clearing any outstanding dues."]
        if decision.top_positive_features:
            feature_tips = {
                "credit_score": "Work on improving your credit score above 700.",
                "monthly_income": "Apply for a lower loan amount relative to your income.",
                "foir_ratio": "Reduce existing EMIs before reapplying.",
                "post_loan_foir": "Try a smaller loan amount or longer repayment tenure.",
                "dpd_12m": "Clear all overdue payments and maintain clean repayment for 6 months.",
                "dpd_24m": "Maintain timely repayments for at least 6 months before reapplying.",
                "active_loans_count": "Close some existing loans before applying for a new one.",
                "inconsistency_score": "Ensure all information provided is accurate and consistent.",
                "prior_rejections_count": "Wait at least 90 days before reapplying.",
            }
            for f in decision.top_positive_features[:2]:
                tip = feature_tips.get(f)
                if tip:
                    tips.append(tip)
        tips.append("Reapply after 90 days for a fresh assessment.")
        return tips
    if not decision.failing_rule:
        return ["Please contact our helpline for assistance."]
    tips_map = {
        "min_age": ["You must be at least 21 years old to apply."],
        "max_age": ["You must be under 65 years old to apply."],
        "min_income": ["Minimum monthly income of ₹15,000 is required.", "Consider applying once your income increases."],
        "bureau_score": ["Improve your CIBIL score to 650+ by repaying existing dues.", "Check your credit report for errors at CIBIL.com."],
        "dpd_24m": ["Clear any overdue payments on existing loans.", "Apply again after 6 months of clean repayment."],
        "foir": ["Reduce your existing EMI obligations below 50% of income before applying."],
        "post_loan_foir": ["Try applying for a smaller loan amount or a longer repayment tenure.", "Reduce existing EMIs first."],
        "liveness": ["Ensure good lighting and a stable connection.", "Try again or contact our helpline."],
        "pincode_exclusion": ["We are unable to service your area currently. Check back later."],
    }
    return tips_map.get(decision.failing_rule, ["Please contact our helpline for assistance."])
