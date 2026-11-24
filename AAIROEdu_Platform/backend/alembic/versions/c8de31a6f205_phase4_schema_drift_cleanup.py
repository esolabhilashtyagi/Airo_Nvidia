"""Align Phase 4-created indexes and constraints with ORM metadata."""
from alembic import op
import sqlalchemy as sa

revision = "c8de31a6f205"
down_revision = "b46ad9e2f014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy models define this as a unique index (not a constraint plus a
    # second non-unique index).
    op.drop_constraint("experience_levels_name_key", "experience_levels", type_="unique")
    op.drop_index("ix_experience_levels_name", table_name="experience_levels")
    op.create_index("ix_experience_levels_name", "experience_levels", ["name"], unique=True)

    for table, index in (
        ("module_job_roles", "ix_module_job_roles_job_role_id"),
        ("module_skills", "ix_module_skills_skill_id"),
        ("question_companies", "ix_question_companies_company_id"),
        ("question_job_roles", "ix_question_job_roles_job_role_id"),
        ("question_skills", "ix_question_skills_skill_id"),
        ("questions", "ix_questions_created_by_id"),
        ("questions", "ix_questions_reviewed_by_id"),
    ):
        op.drop_index(index, table_name=table)

    for table in ("experience_levels", "interview_rounds", "subjects", "topics", "lesson_progress", "resume_rate_limits"):
        op.create_index(f"ix_{table}_id", table, ["id"])


def downgrade() -> None:
    for table in ("experience_levels", "interview_rounds", "subjects", "topics", "lesson_progress", "resume_rate_limits"):
        op.drop_index(f"ix_{table}_id", table_name=table)
    for table, index, column in (
        ("module_job_roles", "ix_module_job_roles_job_role_id", "job_role_id"),
        ("module_skills", "ix_module_skills_skill_id", "skill_id"),
        ("question_companies", "ix_question_companies_company_id", "company_id"),
        ("question_job_roles", "ix_question_job_roles_job_role_id", "job_role_id"),
        ("question_skills", "ix_question_skills_skill_id", "skill_id"),
        ("questions", "ix_questions_created_by_id", "created_by_id"),
        ("questions", "ix_questions_reviewed_by_id", "reviewed_by_id"),
    ):
        op.create_index(index, table, [column])
    op.drop_index("ix_experience_levels_name", table_name="experience_levels")
    op.create_unique_constraint("experience_levels_name_key", "experience_levels", ["name"])
    op.create_index("ix_experience_levels_name", "experience_levels", ["name"])
