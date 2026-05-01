import uuid
from datetime import date
from sqlalchemy import String, Float, Boolean, ForeignKey, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)

    # ── Extracted fields (from LLM Q1–Q8) ────────────────────────────────────
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    address_line: Mapped[str | None] = mapped_column(String(512), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pincode: Mapped[str | None] = mapped_column(String(6), nullable=True)

    employment_type: Mapped[str | None] = mapped_column(String(32), nullable=True)  # salaried/self_employed/business
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    employer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_tenure_years: Mapped[float | None] = mapped_column(Float, nullable=True)

    loan_purpose: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_tenure_months: Mapped[int | None] = mapped_column(nullable=True)

    existing_emi_monthly: Mapped[float | None] = mapped_column(Float, nullable=True)
    has_existing_loans: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # ── LLM quality signals ───────────────────────────────────────────────────
    extraction_confidence_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    inconsistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged_inconsistencies: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── 35-feature vector (assembled before ML scoring) ───────────────────────
    feature_vector: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    session: Mapped["Session"] = relationship(back_populates="application")
