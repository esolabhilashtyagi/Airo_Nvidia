"""Add persistent authentication lockouts and refresh-token sessions.

Revision ID: d72a69b3c410
Revises: a4f2c7d9e108
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d72a69b3c410"
down_revision = "a4f2c7d9e108"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("auth_token_version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_table(
        "auth_attempt_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("endpoint", sa.String(length=20), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("endpoint", "scope", "key_hash", name="uq_auth_attempt_endpoint_scope_key"),
    )
    op.create_index("ix_auth_attempt_locked_until", "auth_attempt_limits", ["locked_until"])
    op.create_table(
        "refresh_token_sessions",
        sa.Column("jti", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_refresh_token_sessions_user_id", "refresh_token_sessions", ["user_id"])
    op.create_index("ix_refresh_token_sessions_family_id", "refresh_token_sessions", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_token_sessions_family_id", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")
    op.drop_index("ix_auth_attempt_locked_until", table_name="auth_attempt_limits")
    op.drop_table("auth_attempt_limits")
    op.drop_column("users", "auth_token_version")
