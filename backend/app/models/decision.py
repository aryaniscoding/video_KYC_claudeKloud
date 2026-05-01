import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), unique=True, nullable=False)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"), nullable=False)

    # ── Layer 1: Hard rules ───────────────────────────────────────────────────
    hard_rules_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failing_rule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failing_rule_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Layer 2: ML scoring ───────────────────────────────────────────────────
    pd_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_band: Mapped[str | None] = mapped_column(String(16), nullable=True)  # LOW/MEDIUM_LOW/etc.
    eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    top_positive_features: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    top_negative_features: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Layer 3: Offer ────────────────────────────────────────────────────────
    approved_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    interest_rate: Mapped[float | None] = mapped_column(Float, nullable=True)   # annual %
    recommended_tenure_months: Mapped[int | None] = mapped_column(nullable=True)
    emi_options: Mapped[list | None] = mapped_column(JSONB, nullable=True)      # [{tenure, emi, total_payable}]
    processing_fee_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    offer_matrix_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    offer_ref_id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, nullable=False, unique=True)
    offer_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    session: Mapped["Session"] = relationship(back_populates="decision")
    offer_pdf: Mapped["OfferPDF | None"] = relationship(back_populates="decision", uselist=False)


class OfferPDF(Base):
    __tablename__ = "offer_pdfs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    decision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decisions.id"), nullable=False)
    offer_ref_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)

    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_hash: Mapped[str] = mapped_column(String(64), nullable=False)   # SHA-256
    download_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    download_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    decision: Mapped["Decision"] = relationship(back_populates="offer_pdf")
