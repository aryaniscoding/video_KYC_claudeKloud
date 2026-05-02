"""add ip_city ip_state ip_zip to sessions

Revision ID: 002
Revises: 001
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("ip_city",  sa.String(128), nullable=True))
    op.add_column("sessions", sa.Column("ip_state", sa.String(128), nullable=True))
    op.add_column("sessions", sa.Column("ip_zip",   sa.String(16),  nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "ip_zip")
    op.drop_column("sessions", "ip_state")
    op.drop_column("sessions", "ip_city")
