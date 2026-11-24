"""Align UUIDMixin id indexes for auth_attempt_limits and resume_ats_reviews.

Revision ID: d9e8f7a6b5c4
Revises: ce91d2f8a6b0
Create Date: 2026-11-23
"""

from alembic import op

revision = "d9e8f7a6b5c4"
down_revision = "ce91d2f8a6b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_auth_attempt_limits_id", "auth_attempt_limits", ["id"])
    op.create_index("ix_resume_ats_reviews_id", "resume_ats_reviews", ["id"])


def downgrade() -> None:
    op.drop_index("ix_resume_ats_reviews_id", table_name="resume_ats_reviews")
    op.drop_index("ix_auth_attempt_limits_id", table_name="auth_attempt_limits")
