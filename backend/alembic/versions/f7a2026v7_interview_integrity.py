"""Add contextual interview provenance and honest evaluation states.

Revision ID: f7a2026v7
Revises: f4a2026v6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f7a2026v7"
down_revision = "f4a2026v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("mock_interviews", sa.Column("interview_type", sa.String(length=50), nullable=False, server_default="complete"))
    op.add_column("mock_interviews", sa.Column("total_questions", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("mock_interviews", sa.Column("evaluation_status", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("interview_questions", sa.Column("source_question_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_interview_questions_source_question_id", "interview_questions", "questions", ["source_question_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_interview_questions_source_question_id", "interview_questions", ["source_question_id"])
    op.add_column("interview_questions", sa.Column("source_provenance", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.alter_column("interview_evaluations", "overall_score", existing_type=sa.Float(), nullable=True)
    op.alter_column("interview_evaluations", "technical_score", existing_type=sa.Float(), nullable=True)
    op.alter_column("interview_evaluations", "domain_score", existing_type=sa.Float(), nullable=True)
    op.alter_column("interview_evaluations", "communication_score", existing_type=sa.Float(), nullable=True)
    op.alter_column("interview_evaluations", "structure_score", existing_type=sa.Float(), nullable=True)
    op.add_column("interview_evaluations", sa.Column("evaluation_status", sa.String(length=32), nullable=False, server_default="legacy_unverified"))
    op.add_column("interview_evaluations", sa.Column("evaluation_provenance", sa.String(length=32), nullable=False, server_default="legacy_unverified"))


def downgrade() -> None:
    op.drop_column("interview_evaluations", "evaluation_provenance")
    op.drop_column("interview_evaluations", "evaluation_status")
    op.alter_column("interview_evaluations", "structure_score", existing_type=sa.Float(), nullable=False, server_default="0")
    op.alter_column("interview_evaluations", "communication_score", existing_type=sa.Float(), nullable=False, server_default="0")
    op.alter_column("interview_evaluations", "domain_score", existing_type=sa.Float(), nullable=False, server_default="0")
    op.alter_column("interview_evaluations", "technical_score", existing_type=sa.Float(), nullable=False, server_default="0")
    op.alter_column("interview_evaluations", "overall_score", existing_type=sa.Float(), nullable=False, server_default="0")
    op.drop_column("interview_questions", "source_provenance")
    op.drop_index("ix_interview_questions_source_question_id", table_name="interview_questions")
    op.drop_constraint("fk_interview_questions_source_question_id", "interview_questions", type_="foreignkey")
    op.drop_column("interview_questions", "source_question_id")
    op.drop_column("mock_interviews", "evaluation_status")
    op.drop_column("mock_interviews", "total_questions")
    op.drop_column("mock_interviews", "interview_type")
