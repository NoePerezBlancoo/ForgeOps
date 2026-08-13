"""add user invitations and notifications

Revision ID: 3f8e1c7a9b42
Revises: 0b6d4e9a2c31
Create Date: 2026-08-13 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3f8e1c7a9b42"
down_revision: str | None = "0b6d4e9a2c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODE = "current_setting('app.access_mode', true)"
COMPANY_ID = "NULLIF(current_setting('app.company_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "user_invitations",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("inviter_id", sa.Uuid(), nullable=True),
        sa.Column("accepted_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["accepted_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
    )
    op.create_index(
        "ix_user_invitations_company_email_created",
        "user_invitations",
        ["company_id", "email", "created_at"],
    )
    op.create_index(
        "ix_user_invitations_company_id", "user_invitations", ["company_id"]
    )
    op.create_index(
        "ix_user_invitations_expires_at", "user_invitations", ["expires_at"]
    )

    op.create_table(
        "notifications",
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.String(length=500), nullable=False),
        sa.Column("href", sa.String(length=500), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id",
            "recipient_id",
            "dedupe_key",
            name="uq_notifications_recipient_dedupe",
        ),
    )
    op.create_index(
        "ix_notifications_recipient_unread_created",
        "notifications",
        ["company_id", "recipient_id", "read_at", "created_at"],
    )
    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])

    _enable_invitation_rls()
    _enable_notification_rls()


def downgrade() -> None:
    for table, policies in (
        ("notifications", ("select", "insert", "update", "delete")),
        ("user_invitations", ("select", "insert", "update", "delete")),
    ):
        for operation in policies:
            op.execute(f"DROP POLICY IF EXISTS {table}_{operation} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("notifications")
    op.drop_table("user_invitations")


def _enable_invitation_rls() -> None:
    table = "user_invitations"
    _enable(table)
    visible = (
        f"{MODE} IN ('platform', 'system', 'auth') "
        f"OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})"
    )
    tenant_write = (
        f"{MODE} IN ('platform', 'system') "
        f"OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})"
    )
    op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({visible})")
    op.execute(f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({tenant_write})")
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
        f"USING ({visible}) WITH CHECK ({visible})"
    )
    op.execute(
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE "
        f"USING ({MODE} IN ('platform', 'system'))"
    )


def _enable_notification_rls() -> None:
    table = "notifications"
    _enable(table)
    tenant_access = (
        f"{MODE} IN ('platform', 'system') "
        f"OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})"
    )
    op.execute(
        f"CREATE POLICY {table}_select ON {table} FOR SELECT USING ({tenant_access})"
    )
    op.execute(
        f"CREATE POLICY {table}_insert ON {table} FOR INSERT WITH CHECK ({tenant_access})"
    )
    op.execute(
        f"CREATE POLICY {table}_update ON {table} FOR UPDATE "
        f"USING ({tenant_access}) WITH CHECK ({tenant_access})"
    )
    op.execute(
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE "
        f"USING ({MODE} IN ('platform', 'system'))"
    )


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
