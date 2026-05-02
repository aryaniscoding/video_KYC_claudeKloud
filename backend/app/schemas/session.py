from __future__ import annotations
import uuid
from datetime import datetime
from pydantic import BaseModel


# ── Session init (returned after JWT validation) ──────────────────────────────

class GeoLocation(BaseModel):
    latitude: float
    longitude: float
    accuracy: float | None = None   # metres, from browser API


class PreSessionRequest(BaseModel):
    """Sent by frontend on session open: GPS coords + device fingerprint."""
    latitude: float | None = None
    longitude: float | None = None
    geo_accuracy: float | None = None
    device_fingerprint: str | None = None


class PreSessionScores(BaseModel):
    geo_risk_score: float
    ip_risk_score: float
    device_risk_score: float
    hard_stop: bool = False
    hard_stop_reason: str | None = None


class SessionInitResponse(BaseModel):
    session_id: str
    token: str | None = None              # JWT echoed back for frontend convenience
    customer_id: uuid.UUID
    customer_name: str
    product_code: str
    is_fast_track: bool
    pre_fill: dict | None = None          # name/DOB/address if fast-track
    scores: PreSessionScores
    livekit_token: str
    livekit_url: str
    policy_ver: str


# ── WebSocket message types ───────────────────────────────────────────────────

class LivenessResult(BaseModel):
    liveness_score: float
    is_live: bool
    spoof_type: str | None = None
    anti_spoof_score: float
    anti_spoof_passed: bool
    face_detected: bool
    face_confidence: float
    frames_analyzed: int
    estimated_age: float | None = None
    estimated_gender: str | None = None
    gender_confidence: float | None = None
    age_range: str | None = None
    age_consistency_score: float | None = None
    active_challenge_required: bool = False
    hitl_required: bool = False


class ConsentResult(BaseModel):
    transcript: str
    consent_confidence: float
    is_valid: bool
    consent_hash: str
    timestamp: datetime
    replay_required: bool = False
    helpline_required: bool = False


class QAChunkResult(BaseModel):
    question_index: int          # 0-based
    partial_transcript: str
    is_final: bool
    auto_advance: bool = False   # silence detected
    word_timestamps: list[dict] | None = None


# ── Offer response ────────────────────────────────────────────────────────────

class EMIOption(BaseModel):
    tenure_months: int
    emi_amount: float
    total_payable: float
    total_interest_inr: float = 0.0


class OfferResponse(BaseModel):
    eligible: bool
    under_review: bool = False
    approved_amount: float | None = None
    interest_rate_pct: float | None = None
    recommended_tenure_months: int | None = None
    emi_options: list[EMIOption] | None = None
    processing_fee_pct: float | None = None
    offer_ref_id: uuid.UUID | None = None
    offer_valid_until: datetime | None = None
    approval_reasons: list[str] | None = None   # plain-English SHAP approval signals
    risk_factors: list[str] | None = None        # plain-English SHAP risk drivers
    decline_reason: str | None = None
    decline_tips: list[str] | None = None
    failing_rule: str | None = None
    risk_band: str | None = None
    pd_score: float | None = None


class DownloadURLResponse(BaseModel):
    download_url: str
    expires_at: datetime
