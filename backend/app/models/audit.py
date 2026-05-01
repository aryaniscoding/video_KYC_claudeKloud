import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from app.models.base import utcnow


class AuditLog(Base):
    """Append-only. Never UPDATE or DELETE rows here."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)

    # LangGraph node that emitted this event
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # Arbitrary payload — features, scores, decisions, SHAP values, etc.
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Versioning snapshot at time of event
    policy_ver: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    session: Mapped["Session"] = relationship(back_populates="audit_events")


class PriorApplication(Base):
    """Historical application records used for the 7-feature history check."""
    __tablename__ = "prior_applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    aadhaar_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # outcome: approved / declined / withdrawn / hitl
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_band: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # loan_performance: good / bad / unknown (populated after repayment history available)
    loan_performance: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)

    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="prior_applications")
