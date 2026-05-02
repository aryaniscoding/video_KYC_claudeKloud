"""
Admin API — all endpoints Atharva's dashboard calls.

POST /admin/login
GET  /admin/customers
POST /admin/customers
POST /admin/send-link
POST /admin/resend-link
GET  /admin/session-status/{session_id}
GET  /admin/hitl-queue
POST /admin/hitl/{session_id}/decision
"""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.config import get_settings
from app.database import get_db
from app.models import AdminUser, Customer, Session, SessionStatus, AuditLog, Decision, Application
from app.schemas.admin import (
    AdminLoginRequest, AdminLoginResponse,
    CustomerCreate, CustomerResponse,
    SendLinkRequest, SendLinkResponse, ResendLinkRequest,
    SessionStatusResponse, ApplicationDetail, DecisionDetail,
    HITLQueueItem, HITLDecisionRequest,
)
from app.services.jwt_service import create_admin_token, create_session_token
from app.services.email_service import send_kyc_link_email
from app.services.s3_service import generate_presigned_url
from passlib.context import CryptContext

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


# ── POST /admin/login ─────────────────────────────────────────────────────────

@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(body: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AdminUser).where(AdminUser.email == body.email))
    admin = result.scalar_one_or_none()

    if not admin or not pwd_ctx.verify(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    token = create_admin_token(admin.id, admin.email)
    return AdminLoginResponse(
        access_token=token,
        token=token,
        name=admin.username,
        admin_id=admin.id,
        email=admin.email,
    )


# ── GET /admin/customers ──────────────────────────────────────────────────────

_STATUS_LABEL = {
    "pending": "Link Sent",
    "started": "In Progress",
    "face_check": "In Progress",
    "consent": "In Progress",
    "qa": "In Progress",
    "processing": "Processing",
    "approved": "Approved",
    "declined": "Declined",
    "hitl": "Manual Review",
    "expired": "Expired",
    "dropped": "Dropped",
}


@router.get("/customers", response_model=list[CustomerResponse])
async def list_customers(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    cust_result = await db.execute(
        select(Customer).order_by(desc(Customer.created_at)).offset(skip).limit(limit)
    )
    customers = cust_result.scalars().all()

    # Fetch latest session per customer in one query
    cust_ids = [c.id for c in customers]
    sess_result = await db.execute(
        select(Session.customer_id, Session.status, Session.token_jti)
        .where(Session.customer_id.in_(cust_ids))
        .order_by(Session.customer_id, desc(Session.created_at))
    )
    latest: dict = {}
    for row in sess_result.all():
        if row.customer_id not in latest:
            latest[row.customer_id] = (row.status, row.token_jti)

    out = []
    for c in customers:
        sess_info = latest.get(c.id)
        raw_status = sess_info[0].value if sess_info else None
        out.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone_last4": c.phone_last4,
            "phone": f"****{c.phone_last4}",
            "pan_number": c.pan_number,
            "product_code": c.product_code,
            "product": c.product_code,
            "credit_score": c.credit_score,
            "created_at": c.created_at,
            "created_date": c.created_at.strftime("%d %b %Y") if c.created_at else "",
            "status": _STATUS_LABEL.get(raw_status, "No Session"),
            "latest_session_id": sess_info[1] if sess_info else None,
        })
    return out


# ── POST /admin/customers ─────────────────────────────────────────────────────

@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    phone_hash = _hash_phone(body.phone)

    # idempotent — return existing if same phone
    result = await db.execute(select(Customer).where(Customer.phone_hash == phone_hash))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    customer = Customer(
        name=body.name,
        email=body.email,
        phone_hash=phone_hash,
        phone_last4=body.phone[-4:],
        pan_number=body.pan_number.upper() if body.pan_number else None,
        product_code=body.product_code,
        credit_score=body.credit_score,
        dpd_12m=body.dpd_12m,
        dpd_24m=body.dpd_24m,
        active_loans_count=body.active_loans_count,
        total_outstanding_inr=body.total_outstanding_inr,
    )
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


# ── POST /admin/send-link ─────────────────────────────────────────────────────

@router.post("/send-link", response_model=SendLinkResponse)
async def send_link(
    body: SendLinkRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Customer).where(Customer.id == body.customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    ttl_seconds = body.ttl_hours * 3600
    token, payload = create_session_token(
        customer_id=customer.id,
        phone_hash=customer.phone_hash,
        product_code=customer.product_code,
        max_amount=float(customer.max_loan_amount),
        ttl_seconds=ttl_seconds,
    )

    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

    session = Session(
        customer_id=customer.id,
        token_jti=payload["jti"],
        policy_ver=payload["policy_ver"],
        product_code=payload["product_code"],
        max_amount=payload["max_amount"],
        token_issued_at=issued_at,
        token_expires_at=expires_at,
        status=SessionStatus.PENDING,
    )
    db.add(session)
    await db.commit()

    kyc_url = f"{settings.frontend_url}/session/{token}"
    email_sent = await send_kyc_link_email(customer.email, customer.name, kyc_url, expires_at)

    return SendLinkResponse(
        session_id=payload["jti"],
        token=token,
        kyc_url=kyc_url,
        expires_at=expires_at,
        email_sent=email_sent,
    )


# ── POST /admin/resend-link ───────────────────────────────────────────────────

@router.post("/resend-link", response_model=SendLinkResponse)
async def resend_link(
    body: ResendLinkRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    # Accept either customer_id (from admin table) or session_id (legacy)
    if body.customer_id:
        result = await db.execute(
            select(Session)
            .where(Session.customer_id == body.customer_id)
            .order_by(desc(Session.created_at))
            .limit(1)
        )
    elif body.session_id:
        result = await db.execute(select(Session).where(Session.token_jti == body.session_id))
    else:
        raise HTTPException(status_code=422, detail="Provide customer_id or session_id")
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Expire the old session, create a fresh one for the same customer
    session.status = SessionStatus.EXPIRED
    await db.commit()

    cust_result = await db.execute(select(Customer).where(Customer.id == session.customer_id))
    customer = cust_result.scalar_one()

    ttl_seconds = settings.session_token_ttl_seconds
    token, payload = create_session_token(
        customer_id=customer.id,
        phone_hash=customer.phone_hash,
        product_code=customer.product_code,
        max_amount=float(customer.max_loan_amount),
        ttl_seconds=ttl_seconds,
    )
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)

    new_session = Session(
        customer_id=customer.id,
        token_jti=payload["jti"],
        policy_ver=payload["policy_ver"],
        product_code=payload["product_code"],
        max_amount=payload["max_amount"],
        token_issued_at=issued_at,
        token_expires_at=expires_at,
        status=SessionStatus.PENDING,
    )
    db.add(new_session)
    await db.commit()

    kyc_url = f"{settings.frontend_url}/session/{token}"
    email_sent = await send_kyc_link_email(customer.email, customer.name, kyc_url, expires_at)

    return SendLinkResponse(
        session_id=payload["jti"],
        token=token,
        kyc_url=kyc_url,
        expires_at=expires_at,
        email_sent=email_sent,
    )


# ── GET /admin/session-status/{session_id} ────────────────────────────────────

@router.get("/session-status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Session).where(Session.token_jti == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cust_result = await db.execute(select(Customer).where(Customer.id == session.customer_id))
    customer = cust_result.scalar_one()

    app_result = await db.execute(select(Application).where(Application.session_id == session.id))
    app = app_result.scalar_one_or_none()

    dec_result = await db.execute(select(Decision).where(Decision.session_id == session.id))
    dec = dec_result.scalar_one_or_none()

    application_detail = None
    if app:
        application_detail = ApplicationDetail(
            full_name=app.full_name,
            dob=app.dob.isoformat() if app.dob else None,
            address_line=app.address_line,
            city=app.city,
            state=app.state,
            pincode=app.pincode,
            employment_type=app.employment_type,
            monthly_income=app.monthly_income,
            employer_name=app.employer_name,
            job_tenure_years=app.job_tenure_years,
            loan_purpose=app.loan_purpose,
            requested_amount=app.requested_amount,
            preferred_tenure_months=app.preferred_tenure_months,
            existing_emi_monthly=app.existing_emi_monthly,
            has_existing_loans=app.has_existing_loans,
            extraction_confidence_avg=app.extraction_confidence_avg,
            inconsistency_score=app.inconsistency_score,
            flagged_inconsistencies=app.flagged_inconsistencies,
        )

    decision_detail = None
    if dec:
        decision_detail = DecisionDetail(
            hard_rules_passed=dec.hard_rules_passed,
            failing_rule=dec.failing_rule,
            failing_rule_reason=dec.failing_rule_reason,
            pd_score=dec.pd_score,
            risk_band=dec.risk_band,
            eligible=dec.eligible,
            top_positive_features=dec.top_positive_features,
            top_negative_features=dec.top_negative_features,
            approved_amount=dec.approved_amount,
            interest_rate=dec.interest_rate,
            recommended_tenure_months=dec.recommended_tenure_months,
            processing_fee_pct=dec.processing_fee_pct,
            emi_options=dec.emi_options,
        )

    liveness_frame_url = None
    if session.liveness_frame_key:
        liveness_frame_url = generate_presigned_url(
            session.liveness_frame_key,
            bucket=settings.s3_bucket_frames,
            expires_seconds=3600,
        )

    return SessionStatusResponse(
        session_id=session.token_jti,
        customer_name=customer.name,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        liveness_frame_url=liveness_frame_url,
        liveness_score=session.liveness_score,
        estimated_age=session.estimated_age,
        estimated_gender=session.estimated_gender,
        gender_confidence=session.gender_confidence,
        age_consistency_score=session.age_consistency_score,
        face_confidence=session.face_confidence,
        anti_spoof_score=session.anti_spoof_score,
        anti_spoof_passed=session.anti_spoof_passed,
        spoof_type=session.spoof_type,
        geo_risk_score=session.geo_risk_score,
        ip_risk_score=session.ip_risk_score,
        device_risk_score=session.device_risk_score,
        ip_address=session.ip_address,
        device_fingerprint=session.device_fingerprint,
        latitude=session.latitude,
        longitude=session.longitude,
        consent_confidence=session.consent_confidence,
        consent_transcript=session.consent_transcript,
        avg_response_latency_ms=session.avg_response_latency_ms,
        hesitation_count=session.hesitation_count,
        question_retry_count=session.question_retry_count,
        velocity_fraud_flag=session.velocity_fraud_flag,
        application=application_detail,
        decision=decision_detail,
    )


# ── GET /admin/hitl-queue ─────────────────────────────────────────────────────

@router.get("/hitl-queue", response_model=list[HITLQueueItem])
async def get_hitl_queue(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    result = await db.execute(
        select(Session, Customer)
        .join(Customer, Session.customer_id == Customer.id)
        .where(Session.status == SessionStatus.HITL)
        .order_by(desc(Session.updated_at))
    )
    rows = result.all()

    items = []
    for session, customer in rows:
        # derive reason from audit log — pick the most recent HITL trigger event
        audit_result = await db.execute(
            select(AuditLog)
            .where(AuditLog.session_id == session.id)
            .where(AuditLog.event_type == "hitl_triggered")
            .order_by(desc(AuditLog.created_at))
            .limit(1)
        )
        audit = audit_result.scalar_one_or_none()
        reason = audit.event_data.get("reason", "unknown") if audit else "unknown"

        items.append(HITLQueueItem(
            session_id=session.token_jti,
            customer_name=customer.name,
            reason=reason,
            created_at=session.updated_at,
        ))
    return items


# ── POST /admin/hitl/{session_id}/decision ────────────────────────────────────

@router.post("/hitl/{session_id}/decision", status_code=status.HTTP_200_OK)
async def hitl_decision(
    session_id: str,
    body: HITLDecisionRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    result = await db.execute(select(Session).where(Session.token_jti == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.HITL:
        raise HTTPException(status_code=400, detail="Session is not in HITL queue")

    if body.decision == "approve":
        session.status = SessionStatus.APPROVED
    elif body.decision == "decline":
        session.status = SessionStatus.DECLINED
    elif body.decision == "resume":
        session.status = SessionStatus.PROCESSING

    log = AuditLog(
        session_id=session.id,
        node_name="hitl_review",
        event_type="hitl_decision",
        event_data={
            "decision": body.decision,
            "notes": body.notes,
            "admin_id": admin["sub"],
        },
        policy_ver=session.policy_ver,
    )
    db.add(log)
    await db.commit()

    return {"status": "ok", "new_status": session.status.value}
