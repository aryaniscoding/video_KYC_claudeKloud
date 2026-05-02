import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    STARTED = "started"
    FACE_CHECK = "face_check"
    CONSENT = "consent"
    QA = "qa"
    PROCESSING = "processing"
    APPROVED = "approved"
    DECLINED = "declined"
    HITL = "hitl"
    EXPIRED = "expired"
    DROPPED = "dropped"


class Session(Base, TimestampMixin):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # JWT fields (frozen at token creation)
    token_jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    policy_ver: Mapped[str] = mapped_column(String(16), nullable=False, default="v1.0")
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    max_amount: Mapped[float] = mapped_column(Float, nullable=False)
    token_issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, native_enum=False), default=SessionStatus.PENDING, nullable=False
    )

    # LiveKit
    livekit_room_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Pre-session scores (0.0 – 1.0)
    geo_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ip_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # GPS coords from browser (if granted)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # IP-derived location (from ip-api.com at session init)
    ip_city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_zip: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # CV signals
    liveness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_age: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gender_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    age_consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    face_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    anti_spoof_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    anti_spoof_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    spoof_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Consent
    consent_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    consent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consent_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Q&A behaviour
    avg_response_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    hesitation_count: Mapped[int | None] = mapped_column(nullable=True)
    question_retry_count: Mapped[int | None] = mapped_column(nullable=True)

    # LangGraph checkpoint reference (stored in postgres via langgraph-checkpoint-postgres)
    langgraph_thread_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Velocity / history flags
    velocity_fraud_flag: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_fast_track: Mapped[bool] = mapped_column(default=False, nullable=False)

    # S3 paths
    recording_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    liveness_frame_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    consent_recording_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="sessions")
    application: Mapped["Application | None"] = relationship(back_populates="session", uselist=False)
    decision: Mapped["Decision | None"] = relationship(back_populates="session", uselist=False)
    audit_events: Mapped[list["AuditLog"]] = relationship(back_populates="session")
