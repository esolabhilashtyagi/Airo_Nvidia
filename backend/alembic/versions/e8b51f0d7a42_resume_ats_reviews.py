"""Persist candidate-specific job description ATS estimates.

Revision ID: e8b51f0d7a42
Revises: d72a69b3c410
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e8b51f0d7a42"
down_revision = "d72a69b3c410"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_ats_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("resume_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_title", sa.String(length=200), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=False),
        sa.Column("ats_score", sa.Float(), nullable=False),
        sa.Column("keyword_match_score", sa.Float(), nullable=False),
        sa.Column("section_match_score", sa.Float(), nullable=False),
        sa.Column("matched_keywords", postgresql.JSONB(), nullable=False),
        sa.Column("missing_keywords", postgresql.JSONB(), nullable=False),
        sa.Column("matched_sections", postgresql.JSONB(), nullable=False),
        sa.Column("missing_sections", postgresql.JSONB(), nullable=False),
        sa.Column("formatting_warnings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_resume_ats_reviews_resume_id", "resume_ats_reviews", ["resume_id"])


def downgrade() -> None:
    op.drop_index("ix_resume_ats_reviews_resume_id", table_name="resume_ats_reviews")
    op.drop_table("resume_ats_reviews")
