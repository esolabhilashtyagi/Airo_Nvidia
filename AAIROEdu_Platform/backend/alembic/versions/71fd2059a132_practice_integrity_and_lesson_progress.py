"""Persist honest practice evaluation state and per-lesson progress.

Revision ID: 71fd2059a132
Revises: 3a81e60df145
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "71fd2059a132"
down_revision = "3a81e60df145"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_questions_is_archived", "questions", ["is_archived"])
    op.alter_column("question_practice_logs", "is_correct", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("question_practice_logs", "score_percentage", existing_type=sa.Float(), nullable=True)
    op.add_column("question_practice_logs", sa.Column("evaluation_status", sa.String(length=32), nullable=False, server_default="evaluated"))
    op.add_column("question_practice_logs", sa.Column("evaluation_provenance", sa.String(length=32), nullable=False, server_default="deterministic"))
    op.create_table(
        "lesson_progress",
        sa.Column("candidate_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lesson_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_profile_id", "lesson_id", name="uq_lesson_progress_candidate_lesson"),
    )
    op.create_index("ix_lesson_progress_candidate_profile_id", "lesson_progress", ["candidate_profile_id"])
    op.create_index("ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_questions_is_archived", table_name="questions")
    op.drop_column("questions", "is_archived")
    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_candidate_profile_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")
    op.drop_column("question_practice_logs", "evaluation_provenance")
    op.drop_column("question_practice_logs", "evaluation_status")
    op.alter_column("question_practice_logs", "score_percentage", existing_type=sa.Float(), nullable=False)
    op.alter_column("question_practice_logs", "is_correct", existing_type=sa.Boolean(), nullable=False)
