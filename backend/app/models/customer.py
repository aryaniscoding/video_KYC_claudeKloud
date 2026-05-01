import uuid
from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Phone stored only as hash — never plain
    phone_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    phone_last4: Mapped[str] = mapped_column(String(4), nullable=False)  # for PDF password

    # Aadhaar hash (optional — for prior-history lookup)
    aadhaar_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    product_code: Mapped[str] = mapped_column(String(32), nullable=False, default="PL_STANDARD")
    max_loan_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=500000)

    # Bureau data (fetched externally, stored here)
    credit_score: Mapped[int | None] = mapped_column(nullable=True)
    dpd_12m: Mapped[int | None] = mapped_column(nullable=True)
    dpd_24m: Mapped[int | None] = mapped_column(nullable=True)
    active_loans_count: Mapped[int | None] = mapped_column(nullable=True)
    total_outstanding_inr: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="customer")
    prior_applications: Mapped[list["PriorApplication"]] = relationship(back_populates="customer")
