"""Add activation state to managed skills."""
from alembic import op
import sqlalchemy as sa

revision = "b46ad9e2f014"
down_revision = "9c7201b4d85e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("skills", "is_active")
