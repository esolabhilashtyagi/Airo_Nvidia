"""Add candidate ownership to configured assessments.

Revision ID: a4f2c7d9e108
Revises: c8de31a6f205
Create Date: 2026-11-18
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4f2c7d9e108"
down_revision: Union[str, None] = "c8de31a6f205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessments",
        sa.Column("candidate_profile_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_assessments_candidate_profile_id_candidate_profiles",
        "assessments",
        "candidate_profiles",
        ["candidate_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_assessments_candidate_profile_id",
        "assessments",
        ["candidate_profile_id"],
    )

    # Historical assessments can only be assigned when all recorded attempts
    # belong to one candidate. Ambiguous and never-started rows are retained,
    # but made inactive and unowned so no candidate can access them.
    op.execute(sa.text("""
        UPDATE assessments AS assessment
        SET candidate_profile_id = owners.candidate_profile_id
        FROM (
            SELECT assessment_id, min(candidate_profile_id::text)::uuid AS candidate_profile_id
            FROM assessment_attempts
            GROUP BY assessment_id
            HAVING count(DISTINCT candidate_profile_id) = 1
        ) AS owners
        WHERE assessment.id = owners.assessment_id
    """))
    op.execute(sa.text("""
        UPDATE assessments
        SET is_active = false
        WHERE candidate_profile_id IS NULL
    """))
    op.create_check_constraint(
        "ck_assessments_owner_required_when_active",
        "assessments",
        "candidate_profile_id IS NOT NULL OR is_active = false",
    )


def downgrade() -> None:
    op.drop_constraint("ck_assessments_owner_required_when_active", "assessments", type_="check")
    op.drop_index("ix_assessments_candidate_profile_id", table_name="assessments")
    op.drop_constraint(
        "fk_assessments_candidate_profile_id_candidate_profiles",
        "assessments",
        type_="foreignkey",
    )
    op.drop_column("assessments", "candidate_profile_id")
