"""Merge paid ATS and profile resume-template migration heads.

Revision ID: b8d4e2a19f63
Revises: 4d28b7ca9150, a3b7c9d2e441
Create Date: 2026-11-25
"""

from alembic import op  # noqa: F401

revision = "b8d4e2a19f63"
down_revision = ("4d28b7ca9150", "a3b7c9d2e441")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
