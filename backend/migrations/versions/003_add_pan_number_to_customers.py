"""add pan_number to customers

Revision ID: 003
Revises: 002
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("pan_number", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "pan_number")
