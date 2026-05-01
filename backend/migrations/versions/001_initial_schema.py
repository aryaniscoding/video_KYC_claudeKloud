"""Initial schema — all tables

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # customers
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("phone_last4", sa.String(4), nullable=False),
        sa.Column("aadhaar_hash", sa.String(64), nullable=True),
        sa.Column("product_code", sa.String(32), nullable=False, server_default="PL_STANDARD"),
        sa.Column("max_loan_amount", sa.Numeric(12, 2), nullable=False, server_default="500000"),
        sa.Column("credit_score", sa.Integer, nullable=True),
        sa.Column("dpd_12m", sa.Integer, nullable=True),
        sa.Column("dpd_24m", sa.Integer, nullable=True),
        sa.Column("active_loans_count", sa.Integer, nullable=True),
        sa.Column("total_outstanding_inr", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # sessions
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("token_jti", sa.String(64), nullable=False, unique=True),
        sa.Column("policy_ver", sa.String(16), nullable=False, server_default="v1.0"),
        sa.Column("product_code", sa.String(32), nullable=False),
        sa.Column("max_amount", sa.Float, nullable=False),
        sa.Column("token_issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("livekit_room_name", sa.String(128), nullable=True),
        sa.Column("geo_risk_score", sa.Float, nullable=True),
        sa.Column("ip_risk_score", sa.Float, nullable=True),
        sa.Column("device_risk_score", sa.Float, nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_fingerprint", sa.String(255), nullable=True),
        sa.Column("liveness_score", sa.Float, nullable=True),
        sa.Column("estimated_age", sa.Float, nullable=True),
        sa.Column("age_consistency_score", sa.Float, nullable=True),
        sa.Column("face_confidence", sa.Float, nullable=True),
        sa.Column("consent_confidence", sa.Float, nullable=True),
        sa.Column("consent_hash", sa.String(64), nullable=True),
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_transcript", sa.Text, nullable=True),
        sa.Column("avg_response_latency_ms", sa.Float, nullable=True),
        sa.Column("hesitation_count", sa.Integer, nullable=True),
        sa.Column("question_retry_count", sa.Integer, nullable=True),
        sa.Column("langgraph_thread_id", sa.String(64), nullable=True),
        sa.Column("velocity_fraud_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_fast_track", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("recording_path", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_sessions_customer_id", "sessions", ["customer_id"])
    op.create_index("ix_sessions_status", "sessions", ["status"])

    # applications
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False, unique=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("dob", sa.Date, nullable=True),
        sa.Column("address_line", sa.String(512), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("state", sa.String(64), nullable=True),
        sa.Column("pincode", sa.String(6), nullable=True),
        sa.Column("employment_type", sa.String(32), nullable=True),
        sa.Column("monthly_income", sa.Float, nullable=True),
        sa.Column("employer_name", sa.String(255), nullable=True),
        sa.Column("job_tenure_years", sa.Float, nullable=True),
        sa.Column("loan_purpose", sa.String(128), nullable=True),
        sa.Column("requested_amount", sa.Float, nullable=True),
        sa.Column("preferred_tenure_months", sa.Integer, nullable=True),
        sa.Column("existing_emi_monthly", sa.Float, nullable=True),
        sa.Column("has_existing_loans", sa.Boolean, nullable=True),
        sa.Column("extraction_confidence_avg", sa.Float, nullable=True),
        sa.Column("inconsistency_score", sa.Float, nullable=True),
        sa.Column("flagged_inconsistencies", JSONB, nullable=True),
        sa.Column("feature_vector", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # decisions
    op.create_table(
        "decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False, unique=True),
        sa.Column("application_id", UUID(as_uuid=True), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("hard_rules_passed", sa.Boolean, nullable=False),
        sa.Column("failing_rule", sa.String(64), nullable=True),
        sa.Column("failing_rule_reason", sa.String(512), nullable=True),
        sa.Column("pd_score", sa.Float, nullable=True),
        sa.Column("risk_band", sa.String(16), nullable=True),
        sa.Column("eligible", sa.Boolean, nullable=True),
        sa.Column("shap_values", JSONB, nullable=True),
        sa.Column("top_positive_features", JSONB, nullable=True),
        sa.Column("top_negative_features", JSONB, nullable=True),
        sa.Column("model_version", sa.String(32), nullable=True),
        sa.Column("approved_amount", sa.Float, nullable=True),
        sa.Column("interest_rate", sa.Float, nullable=True),
        sa.Column("recommended_tenure_months", sa.Integer, nullable=True),
        sa.Column("emi_options", JSONB, nullable=True),
        sa.Column("processing_fee_pct", sa.Float, nullable=True),
        sa.Column("offer_matrix_version", sa.String(32), nullable=True),
        sa.Column("offer_ref_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("offer_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
    )

    # offer_pdfs
    op.create_table(
        "offer_pdfs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("decision_id", UUID(as_uuid=True), sa.ForeignKey("decisions.id"), nullable=False),
        sa.Column("offer_ref_id", UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("pdf_hash", sa.String(64), nullable=False),
        sa.Column("download_url", sa.String(2048), nullable=True),
        sa.Column("download_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("node_name", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("policy_ver", sa.String(16), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_session_id", "audit_log", ["session_id"])
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"])

    # prior_applications
    op.create_table(
        "prior_applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("phone_hash", sa.String(64), nullable=False),
        sa.Column("aadhaar_hash", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("risk_band", sa.String(16), nullable=True),
        sa.Column("loan_performance", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_prior_apps_customer_id", "prior_applications", ["customer_id"])
    op.create_index("ix_prior_apps_phone_hash", "prior_applications", ["phone_hash"])


def downgrade() -> None:
    op.drop_table("prior_applications")
    op.drop_table("audit_log")
    op.drop_table("offer_pdfs")
    op.drop_table("decisions")
    op.drop_table("applications")
    op.drop_table("sessions")
    op.drop_table("customers")
    op.drop_table("admin_users")
