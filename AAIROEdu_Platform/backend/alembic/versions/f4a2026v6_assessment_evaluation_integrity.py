"""Add explicit assessment evaluation state and configured marking rules.

Revision ID: f4a2026v6
Revises: 71fd2059a132
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f4a2026v6"
down_revision = "71fd2059a132"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assessments", sa.Column("marks_per_question", sa.Float(), nullable=False, server_default="10"))
    op.add_column("assessments", sa.Column("negative_marking_points", sa.Float(), nullable=False, server_default="0"))
    op.add_column("assessments", sa.Column("randomize_questions", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("candidate_answers", "score_awarded", existing_type=sa.Float(), nullable=True)
    op.add_column("candidate_answers", sa.Column("evaluation_status", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("candidate_answers", sa.Column("evaluation_provenance", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("candidate_answers", sa.Column("rubric_breakdown", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("candidate_answers", sa.Column("missing_concepts", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.alter_column("assessment_results", "percentage", existing_type=sa.Float(), nullable=True)
    op.alter_column("assessment_results", "passed", existing_type=sa.Boolean(), nullable=True)
    op.add_column("assessment_results", sa.Column("evaluation_status", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("assessment_results", sa.Column("evaluation_provenance", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("assessment_results", sa.Column("question_feedback", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")))


def downgrade() -> None:
    op.drop_column("assessment_results", "question_feedback")
    op.drop_column("assessment_results", "evaluation_provenance")
    op.drop_column("assessment_results", "evaluation_status")
    op.alter_column("assessment_results", "passed", existing_type=sa.Boolean(), nullable=False, server_default=sa.false())
    op.alter_column("assessment_results", "percentage", existing_type=sa.Float(), nullable=False, server_default="0")
    op.drop_column("candidate_answers", "missing_concepts")
    op.drop_column("candidate_answers", "rubric_breakdown")
    op.drop_column("candidate_answers", "evaluation_provenance")
    op.drop_column("candidate_answers", "evaluation_status")
    op.alter_column("candidate_answers", "score_awarded", existing_type=sa.Float(), nullable=False, server_default="0")
    op.drop_column("assessments", "randomize_questions")
    op.drop_column("assessments", "negative_marking_points")
    op.drop_column("assessments", "marks_per_question")
