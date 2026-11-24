"""Complete relational question taxonomy, revision lifecycle, and module mappings.

Revision ID: 6b14f2c4a901
Revises: f7a2026v7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "6b14f2c4a901"
down_revision = "f7a2026v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("industry_categories", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("""WITH duplicates AS (
        SELECT id, row_number() OVER (PARTITION BY industry_id, name ORDER BY created_at, id) AS n
        FROM industry_categories
    ) DELETE FROM industry_categories c USING duplicates d WHERE c.id=d.id AND d.n>1""")
    op.create_unique_constraint("uq_industry_category_name", "industry_categories", ["industry_id", "name"])

    op.create_table(
        "subjects",
        sa.Column("industry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["industry_id"], ["industries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("industry_id", "name", name="uq_subject_industry_name"),
    )
    op.create_index("ix_subjects_industry_id", "subjects", ["industry_id"])
    op.create_index("ix_subjects_name", "subjects", ["name"])
    op.create_table(
        "topics",
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subject_id", "name", name="uq_topic_subject_name"),
    )
    op.create_index("ix_topics_subject_id", "topics", ["subject_id"])
    op.create_index("ix_topics_name", "topics", ["name"])
    op.execute("""INSERT INTO subjects (id, industry_id, name, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), industry_id, subject, true, now(), now()
        FROM questions GROUP BY industry_id, subject ON CONFLICT (industry_id, name) DO NOTHING""")
    op.execute("""INSERT INTO topics (id, subject_id, name, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), s.id, q.topic, true, now(), now()
        FROM (SELECT DISTINCT industry_id, subject, topic FROM questions) q
        JOIN subjects s ON s.industry_id=q.industry_id AND s.name=q.subject
        ON CONFLICT (subject_id, name) DO NOTHING""")

    op.add_column("companies", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("questions", sa.Column("industry_category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("experience_level", sa.String(length=100), nullable=True))
    op.add_column("questions", sa.Column("source_url", sa.String(length=2000), nullable=True))
    op.add_column("questions", sa.Column("marks", sa.Float(), nullable=True))
    op.add_column("questions", sa.Column("estimated_minutes", sa.Integer(), nullable=True))
    op.add_column("questions", sa.Column("workflow_status", sa.String(length=32), nullable=False, server_default="pending_review"))
    op.add_column("questions", sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("questions", sa.Column("root_question_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("questions", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("questions", sa.Column("review_comment", sa.Text(), nullable=True))
    op.add_column("questions", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("questions", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("questions", "expected_answer", existing_type=sa.Text(), nullable=True)
    op.create_foreign_key("fk_questions_industry_category", "questions", "industry_categories", ["industry_category_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_questions_subject", "questions", "subjects", ["subject_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_questions_topic", "questions", "topics", ["topic_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_questions_root_question", "questions", "questions", ["root_question_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_questions_created_by", "questions", "users", ["created_by_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_questions_reviewed_by", "questions", "users", ["reviewed_by_id"], ["id"], ondelete="SET NULL")
    for column in ("industry_category_id", "subject_id", "topic_id", "experience_level", "workflow_status", "root_question_id", "created_by_id", "reviewed_by_id"):
        op.create_index(f"ix_questions_{column}", "questions", [column])
    op.create_unique_constraint("uq_question_revision_number", "questions", ["root_question_id", "version_number"])
    op.execute("UPDATE questions SET root_question_id=id")
    op.execute("""UPDATE questions SET workflow_status=CASE
        WHEN is_archived THEN 'archived'
        WHEN approval_status='approved' THEN 'published'
        WHEN approval_status='rejected' THEN 'rejected'
        ELSE 'pending_review' END""")
    op.execute("UPDATE questions SET published_at=created_at WHERE workflow_status='published'")
    op.execute("UPDATE questions SET reviewed_at=updated_at WHERE approval_status IN ('approved','rejected')")
    op.execute("UPDATE questions SET subject_id=s.id FROM subjects s WHERE s.industry_id=questions.industry_id AND s.name=questions.subject")
    op.execute("UPDATE questions SET topic_id=t.id FROM topics t WHERE t.name=questions.topic AND t.subject_id=questions.subject_id")
    op.execute("UPDATE questions SET experience_level=r.experience_level FROM job_roles r WHERE r.id=questions.job_role_id")

    op.create_table(
        "question_job_roles",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_role_id"], ["job_roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("question_id", "job_role_id"),
    )
    op.create_index("ix_question_job_roles_job_role_id", "question_job_roles", ["job_role_id"])
    op.execute("INSERT INTO question_job_roles (question_id, job_role_id) SELECT id, job_role_id FROM questions WHERE job_role_id IS NOT NULL ON CONFLICT DO NOTHING")
    op.create_table(
        "question_skills",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("question_id", "skill_id"),
    )
    op.create_index("ix_question_skills_skill_id", "question_skills", ["skill_id"])
    op.create_table(
        "question_companies",
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("question_id", "company_id"),
    )
    op.create_index("ix_question_companies_company_id", "question_companies", ["company_id"])

    op.add_column("modules", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_modules_is_archived", "modules", ["is_archived"])
    op.create_table(
        "module_job_roles",
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_role_id"], ["job_roles.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("module_id", "job_role_id"),
    )
    op.create_index("ix_module_job_roles_job_role_id", "module_job_roles", ["job_role_id"])
    op.create_table(
        "module_skills",
        sa.Column("module_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("module_id", "skill_id"),
    )
    op.create_index("ix_module_skills_skill_id", "module_skills", ["skill_id"])
    op.execute("""UPDATE candidate_module_progress p SET completion_percentage=g.max_percentage,
        status=CASE WHEN g.max_percentage >= 100 THEN 'completed'::module_progress_status_enum ELSE p.status END
        FROM (SELECT candidate_profile_id, module_id, max(completion_percentage) AS max_percentage
              FROM candidate_module_progress GROUP BY candidate_profile_id, module_id) g
        WHERE p.candidate_profile_id=g.candidate_profile_id AND p.module_id=g.module_id""")
    op.execute("""WITH duplicates AS (
        SELECT id, row_number() OVER (PARTITION BY candidate_profile_id, module_id ORDER BY updated_at DESC, id) AS n
        FROM candidate_module_progress
    ) DELETE FROM candidate_module_progress p USING duplicates d WHERE p.id=d.id AND d.n>1""")
    op.create_unique_constraint("uq_candidate_module_progress", "candidate_module_progress", ["candidate_profile_id", "module_id"])


def downgrade() -> None:
    op.drop_constraint("uq_candidate_module_progress", "candidate_module_progress", type_="unique")
    for table, idx in [("module_skills", "ix_module_skills_skill_id"), ("module_job_roles", "ix_module_job_roles_job_role_id")]:
        op.drop_index(idx, table_name=table)
        op.drop_table(table)
    op.drop_index("ix_modules_is_archived", table_name="modules")
    op.drop_column("modules", "is_archived")
    for table, idx in [("question_companies", "ix_question_companies_company_id"), ("question_skills", "ix_question_skills_skill_id"), ("question_job_roles", "ix_question_job_roles_job_role_id")]:
        op.drop_index(idx, table_name=table)
        op.drop_table(table)
    op.drop_constraint("uq_question_revision_number", "questions", type_="unique")
    for column, constraint in [("reviewed_by_id", "fk_questions_reviewed_by"), ("created_by_id", "fk_questions_created_by"), ("root_question_id", "fk_questions_root_question"), ("topic_id", "fk_questions_topic"), ("subject_id", "fk_questions_subject"), ("industry_category_id", "fk_questions_industry_category")]:
        op.drop_constraint(constraint, "questions", type_="foreignkey")
    for column in ("industry_category_id", "subject_id", "topic_id", "experience_level", "workflow_status", "root_question_id", "created_by_id", "reviewed_by_id"):
        op.drop_index(f"ix_questions_{column}", table_name="questions")
    for column in ("archived_at", "published_at", "review_comment", "reviewed_at", "reviewed_by_id", "created_by_id", "root_question_id", "version_number", "workflow_status", "estimated_minutes", "marks", "source_url", "experience_level", "topic_id", "subject_id", "industry_category_id"):
        op.drop_column("questions", column)
    op.alter_column("questions", "expected_answer", existing_type=sa.Text(), nullable=False)
    op.drop_index("ix_topics_name", table_name="topics")
    op.drop_index("ix_topics_subject_id", table_name="topics")
    op.drop_table("topics")
    op.drop_index("ix_subjects_name", table_name="subjects")
    op.drop_index("ix_subjects_industry_id", table_name="subjects")
    op.drop_table("subjects")
    op.drop_column("companies", "is_active")
    op.drop_constraint("uq_industry_category_name", "industry_categories", type_="unique")
    op.drop_column("industry_categories", "is_active")
