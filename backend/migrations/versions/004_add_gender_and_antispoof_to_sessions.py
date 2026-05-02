"""add gender and anti-spoof fields to sessions

Revision ID: 004
Revises: 003
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("estimated_gender", sa.String(16), nullable=True))
    op.add_column("sessions", sa.Column("gender_confidence", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("anti_spoof_score", sa.Float(), nullable=True))
    op.add_column("sessions", sa.Column("anti_spoof_passed", sa.Boolean(), nullable=True))
    op.add_column("sessions", sa.Column("spoof_type", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "spoof_type")
    op.drop_column("sessions", "anti_spoof_passed")
    op.drop_column("sessions", "anti_spoof_score")
    op.drop_column("sessions", "gender_confidence")
    op.drop_column("sessions", "estimated_gender")
