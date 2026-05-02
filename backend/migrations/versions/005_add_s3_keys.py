"""Add liveness_frame_key and consent_recording_key to sessions

Revision ID: 005
Revises: 004
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("liveness_frame_key", sa.String(512), nullable=True))
    op.add_column("sessions", sa.Column("consent_recording_key", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "consent_recording_key")
    op.drop_column("sessions", "liveness_frame_key")
