"""Store the candidate's optional avatar appearance selection.

Revision ID: 4d28b7ca9150
Revises: 3b17c4d8a902
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa

revision = "4d28b7ca9150"
down_revision = "3b17c4d8a902"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_profiles", sa.Column("avatar_gender", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("candidate_profiles", "avatar_gender")
