"""Add richer resume profile fields and premium layout purchases.

Revision ID: a3b7c9d2e441
Revises: d9e8f7a6b5c4
Create Date: 2026-11-25
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a3b7c9d2e441"
down_revision = "d9e8f7a6b5c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("professional_summary", sa.Text(), nullable=True))
    op.add_column("candidate_profiles", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("candidate_profiles", sa.Column("location", sa.String(length=255), nullable=True))
    op.add_column("candidate_profiles", sa.Column("linkedin_url", sa.String(length=500), nullable=True))
    op.add_column("candidate_profiles", sa.Column("github_url", sa.String(length=500), nullable=True))
    op.add_column("candidate_profiles", sa.Column("certifications", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("candidate_profiles", sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.execute("UPDATE candidate_profiles SET certifications = '[]'::jsonb WHERE certifications IS NULL")
    op.execute("UPDATE candidate_profiles SET projects = '[]'::jsonb WHERE projects IS NULL")
    op.alter_column("candidate_profiles", "certifications", nullable=False)
    op.alter_column("candidate_profiles", "projects", nullable=False)
    op.create_table(
        "resume_template_payments",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=80), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=80), nullable=True),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_order_id", name="uq_resume_template_payment_order"),
        sa.UniqueConstraint("razorpay_payment_id", name="uq_resume_template_payment_payment"),
    )
    op.create_index("ix_resume_template_payments_user_id", "resume_template_payments", ["user_id"])
    op.create_index("ix_resume_template_payments_id", "resume_template_payments", ["id"])


def downgrade() -> None:
    op.drop_index("ix_resume_template_payments_id", table_name="resume_template_payments")
    op.drop_index("ix_resume_template_payments_user_id", table_name="resume_template_payments")
    op.drop_table("resume_template_payments")
    op.drop_column("candidate_profiles", "projects")
    op.drop_column("candidate_profiles", "certifications")
    op.drop_column("candidate_profiles", "github_url")
    op.drop_column("candidate_profiles", "linkedin_url")
    op.drop_column("candidate_profiles", "location")
    op.drop_column("candidate_profiles", "phone")
    op.drop_column("candidate_profiles", "professional_summary")
