"""add platform operator control

Revision ID: b72d9a31c4e8
Revises: a91c7d4e5f60
Create Date: 2026-08-12 21:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b72d9a31c4e8"
down_revision: str | None = "a91c7d4e5f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_operators",
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("mfa_secret_encrypted", sa.String(length=512), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_mfa_counter", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_operators_email", "platform_operators", ["email"], unique=True)
    op.create_index("ix_platform_operators_active", "platform_operators", ["active"])
    op.create_index("ix_platform_operators_locked_until", "platform_operators", ["locked_until"])

    op.create_table(
        "operator_sessions",
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["platform_operators.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operator_sessions_operator_id", "operator_sessions", ["operator_id"])
    op.create_index(
        "ix_operator_sessions_token_hash", "operator_sessions", ["token_hash"], unique=True
    )
    op.create_index("ix_operator_sessions_expires_at", "operator_sessions", ["expires_at"])

    op.create_table(
        "operator_audit_events",
        sa.Column("operator_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("target_type", sa.String(length=48), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["platform_operators.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_operator_audit_events_operator_id", "operator_audit_events", ["operator_id"])
    op.create_index("ix_operator_audit_events_action", "operator_audit_events", ["action"])
    op.create_index("ix_operator_audit_events_target_type", "operator_audit_events", ["target_type"])
    op.create_index("ix_operator_audit_created", "operator_audit_events", ["created_at"])
    op.create_index("ix_operator_audit_target", "operator_audit_events", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_operator_audit_target", table_name="operator_audit_events")
    op.drop_index("ix_operator_audit_created", table_name="operator_audit_events")
    op.drop_index("ix_operator_audit_events_target_type", table_name="operator_audit_events")
    op.drop_index("ix_operator_audit_events_action", table_name="operator_audit_events")
    op.drop_index("ix_operator_audit_events_operator_id", table_name="operator_audit_events")
    op.drop_table("operator_audit_events")
    op.drop_index("ix_operator_sessions_expires_at", table_name="operator_sessions")
    op.drop_index("ix_operator_sessions_token_hash", table_name="operator_sessions")
    op.drop_index("ix_operator_sessions_operator_id", table_name="operator_sessions")
    op.drop_table("operator_sessions")
    op.drop_index("ix_platform_operators_locked_until", table_name="platform_operators")
    op.drop_index("ix_platform_operators_active", table_name="platform_operators")
    op.drop_index("ix_platform_operators_email", table_name="platform_operators")
    op.drop_table("platform_operators")
