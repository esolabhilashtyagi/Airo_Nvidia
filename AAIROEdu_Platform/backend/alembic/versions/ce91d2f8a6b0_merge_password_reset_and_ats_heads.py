"""Merge password reset and ATS review migration heads.

Revision ID: ce91d2f8a6b0
Revises: ba2026v8, e8b51f0d7a42
Create Date: 2026-11-23
"""

from alembic import op  # noqa: F401

revision = "ce91d2f8a6b0"
down_revision = ("ba2026v8", "e8b51f0d7a42")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
