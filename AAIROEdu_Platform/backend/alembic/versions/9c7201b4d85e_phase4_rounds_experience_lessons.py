"""Add queryable experience/round records and progress-preserving lesson archive.

Revision ID: 9c7201b4d85e
Revises: 6b14f2c4a901
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9c7201b4d85e"
down_revision = "6b14f2c4a901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "experience_levels",
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("name"),
    )
    op.create_index("ix_experience_levels_name", "experience_levels", ["name"])
    op.create_table(
        "interview_rounds",
        sa.Column("industry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["industry_id"], ["industries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("industry_id", "name", name="uq_interview_round_industry_name"),
    )
    op.create_index("ix_interview_rounds_industry_id", "interview_rounds", ["industry_id"])
    op.create_index("ix_interview_rounds_name", "interview_rounds", ["name"])
    op.execute("""INSERT INTO experience_levels (id, name, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), experience_level, true, now(), now() FROM job_roles
        WHERE nullif(trim(experience_level), '') IS NOT NULL GROUP BY experience_level
        ON CONFLICT (name) DO NOTHING""")
    op.execute("""INSERT INTO interview_rounds (id, industry_id, name, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), industry_id, interview_round, true, now(), now()
        FROM questions GROUP BY industry_id, interview_round
        ON CONFLICT (industry_id, name) DO NOTHING""")
    op.add_column("questions", sa.Column("experience_level_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("interview_round_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_questions_experience_level", "questions", "experience_levels", ["experience_level_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_questions_interview_round", "questions", "interview_rounds", ["interview_round_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_questions_experience_level_id", "questions", ["experience_level_id"])
    op.create_index("ix_questions_interview_round_id", "questions", ["interview_round_id"])
    op.execute("UPDATE questions SET experience_level_id=e.id FROM experience_levels e WHERE e.name=questions.experience_level")
    op.execute("UPDATE questions SET interview_round_id=r.id FROM interview_rounds r WHERE r.industry_id=questions.industry_id AND r.name=questions.interview_round")
    op.add_column("lessons", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_lessons_is_archived", "lessons", ["is_archived"])
    op.execute("""WITH duplicates AS (
        SELECT id, row_number() OVER (PARTITION BY candidate_profile_id, question_id ORDER BY updated_at DESC, id) AS n
        FROM question_bookmarks
    ) DELETE FROM question_bookmarks b USING duplicates d WHERE b.id=d.id AND d.n>1""")
    op.create_unique_constraint("uq_question_bookmark_candidate_question", "question_bookmarks", ["candidate_profile_id", "question_id"])


def downgrade() -> None:
    op.drop_constraint("uq_question_bookmark_candidate_question", "question_bookmarks", type_="unique")
    op.drop_index("ix_lessons_is_archived", table_name="lessons")
    op.drop_column("lessons", "is_archived")
    op.drop_index("ix_questions_interview_round_id", table_name="questions")
    op.drop_index("ix_questions_experience_level_id", table_name="questions")
    op.drop_constraint("fk_questions_interview_round", "questions", type_="foreignkey")
    op.drop_constraint("fk_questions_experience_level", "questions", type_="foreignkey")
    op.drop_column("questions", "interview_round_id")
    op.drop_column("questions", "experience_level_id")
    op.drop_index("ix_interview_rounds_name", table_name="interview_rounds")
    op.drop_index("ix_interview_rounds_industry_id", table_name="interview_rounds")
    op.drop_table("interview_rounds")
    op.drop_index("ix_experience_levels_name", table_name="experience_levels")
    op.drop_table("experience_levels")
