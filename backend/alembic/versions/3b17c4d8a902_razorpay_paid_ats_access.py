"""Add verified Razorpay entitlement records for paid ATS access.

Revision ID: 3b17c4d8a902
Revises: d9e8f7a6b5c4
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3b17c4d8a902"
down_revision = "d9e8f7a6b5c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ats_access_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("razorpay_order_id", sa.String(length=80), nullable=False),
        sa.Column("razorpay_payment_id", sa.String(length=80), nullable=True),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("razorpay_order_id", name="uq_ats_access_payment_order"),
        sa.UniqueConstraint("razorpay_payment_id", name="uq_ats_access_payment_payment"),
    )
    op.create_index("ix_ats_access_payments_id", "ats_access_payments", ["id"])
    op.create_index("ix_ats_access_payments_user_id", "ats_access_payments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ats_access_payments_user_id", table_name="ats_access_payments")
    op.drop_index("ix_ats_access_payments_id", table_name="ats_access_payments")
    op.drop_table("ats_access_payments")
