"""Extend resume extraction, analysis status, and version metadata.

Revision ID: 2b8ce1a40f57
Revises: 6fba03f321f2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "2b8ce1a40f57"
down_revision = "6fba03f321f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("original_parsed_data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("resumes", sa.Column("analysis_status", sa.String(length=50), nullable=False, server_default="analysis_pending"))
    op.add_column("resumes", sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="0"))
    op.add_column("resumes", sa.Column("extraction_error", sa.Text(), nullable=True))
    op.add_column("resumes", sa.Column("analysis_error", sa.Text(), nullable=True))
    op.add_column("resume_analyses", sa.Column("category_scores", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("resume_analyses", sa.Column("strengths", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("resume_analyses", sa.Column("weaknesses", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("resume_analyses", sa.Column("scoring_explanation", sa.Text(), nullable=True))
    op.add_column("resume_analyses", sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="0"))
    op.add_column("resume_analyses", sa.Column("status", sa.String(length=50), nullable=False, server_default="analysis_completed"))
    op.add_column("resume_analyses", sa.Column("analysis_provider", sa.String(length=50), nullable=True))
    op.add_column("resume_suggestions", sa.Column("supporting_context", sa.Text(), nullable=True))
    op.alter_column("resumes", "parsing_status", server_default="uploaded")


def downgrade() -> None:
    op.drop_column("resume_suggestions", "supporting_context")
    op.drop_column("resume_analyses", "analysis_provider")
    op.drop_column("resume_analyses", "status")
    op.drop_column("resume_analyses", "extraction_confidence")
    op.drop_column("resume_analyses", "scoring_explanation")
    op.drop_column("resume_analyses", "weaknesses")
    op.drop_column("resume_analyses", "strengths")
    op.drop_column("resume_analyses", "category_scores")
    op.drop_column("resumes", "analysis_error")
    op.drop_column("resumes", "extraction_error")
    op.drop_column("resumes", "extraction_confidence")
    op.drop_column("resumes", "analysis_status")
    op.drop_column("resumes", "original_parsed_data")
