from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    token: str                 # same as access_token — for frontend compatibility
    name: str                  # admin display name
    admin_id: uuid.UUID
    email: str


# ── Customer management ───────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    pan_number: str | None = Field(default=None, pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]$", description="10-character PAN")
    product_code: str = Field(default="PL_STANDARD")
    credit_score: int | None = Field(default=None, ge=300, le=900)
    dpd_12m: int | None = None
    dpd_24m: int | None = None
    active_loans_count: int | None = None
    total_outstanding_inr: float | None = None


class CustomerResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone_last4: str
    phone: str = ""                    # "****3210" — masked display
    pan_number: str | None = None
    product_code: str
    product: str = ""                  # alias for product_code
    credit_score: int | None
    created_at: datetime
    created_date: str = ""             # "28 Apr 2026" formatted
    status: str = "No Session"         # latest session status label
    latest_session_id: str | None = None

    model_config = {"from_attributes": True}


# ── Send link ─────────────────────────────────────────────────────────────────

class SendLinkRequest(BaseModel):
    customer_id: uuid.UUID
    ttl_hours: int = Field(default=24, ge=1, le=72)


class SendLinkResponse(BaseModel):
    session_id: str
    token: str
    kyc_url: str
    expires_at: datetime
    email_sent: bool


class ResendLinkRequest(BaseModel):
    session_id: str | None = None
    customer_id: uuid.UUID | None = None


# ── Session status ────────────────────────────────────────────────────────────

class ApplicationDetail(BaseModel):
    full_name: str | None = None
    dob: str | None = None
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    pincode: str | None = None
    employment_type: str | None = None
    monthly_income: float | None = None
    employer_name: str | None = None
    job_tenure_years: float | None = None
    loan_purpose: str | None = None
    preferred_tenure_months: int | None = None
    existing_emi_monthly: float | None = None
    has_existing_loans: bool | None = None
    extraction_confidence_avg: float | None = None
    inconsistency_score: float | None = None
    flagged_inconsistencies: list | None = None


class DecisionDetail(BaseModel):
    hard_rules_passed: bool | None = None
    failing_rule: str | None = None
    failing_rule_reason: str | None = None
    pd_score: float | None = None
    risk_band: str | None = None
    eligible: bool | None = None
    top_positive_features: list | None = None
    top_negative_features: list | None = None
    approved_amount: float | None = None
    interest_rate: float | None = None
    recommended_tenure_months: int | None = None
    processing_fee_pct: float | None = None
    emi_options: list | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    customer_name: str
    status: str
    created_at: datetime
    updated_at: datetime

    # CV / liveness
    liveness_score: float | None = None
    estimated_age: float | None = None
    estimated_gender: str | None = None
    gender_confidence: float | None = None
    age_consistency_score: float | None = None
    face_confidence: float | None = None
    anti_spoof_score: float | None = None
    anti_spoof_passed: bool | None = None
    spoof_type: str | None = None

    # Session signals
    geo_risk_score: float | None = None
    ip_risk_score: float | None = None
    device_risk_score: float | None = None
    ip_address: str | None = None
    device_fingerprint: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Consent / behaviour
    consent_confidence: float | None = None
    consent_transcript: str | None = None
    avg_response_latency_ms: float | None = None
    hesitation_count: int | None = None
    question_retry_count: int | None = None
    velocity_fraud_flag: bool | None = None

    # Application data
    application: ApplicationDetail | None = None

    # Decision
    decision: DecisionDetail | None = None

    model_config = {"from_attributes": True}


# ── HITL queue ────────────────────────────────────────────────────────────────

class HITLQueueItem(BaseModel):
    session_id: str
    customer_name: str
    reason: str       # velocity_flag / liveness_fail / low_confidence
    created_at: datetime

    model_config = {"from_attributes": True}


class HITLDecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|decline|resume)$")
    notes: str | None = None
