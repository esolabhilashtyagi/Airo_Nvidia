"""Persist candidate-scoped resume API rate-limit counters.

Revision ID: 3a81e60df145
Revises: 8ac37d11e09b
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3a81e60df145"
down_revision = "8ac37d11e09b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_rate_limits",
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(length=40), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_profile_id", "operation", name="uq_resume_rate_candidate_operation"),
    )


def downgrade() -> None:
    op.drop_table("resume_rate_limits")
