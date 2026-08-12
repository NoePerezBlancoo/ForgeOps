"""add v1 commercial administration

Revision ID: 8e859f5d3715
Revises: c098bdf2b89f
Create Date: 2026-08-12 17:13:30.858732
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8e859f5d3715"
down_revision: str | None = "c098bdf2b89f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_company_created", "audit_events", ["company_id", "created_at"]
    )
    op.create_index(
        "ix_audit_company_entity",
        "audit_events",
        ["company_id", "entity_type", "entity_id"],
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_company_id", "audit_events", ["company_id"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])

    op.add_column("companies", sa.Column("industry", sa.String(length=120)))
    op.add_column(
        "companies",
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Europe/Madrid",
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column("locale", sa.String(length=16), server_default="es-ES", nullable=False),
    )
    op.add_column(
        "companies",
        sa.Column(
            "work_order_prefix", sa.String(length=8), server_default="OT", nullable=False
        ),
    )
    op.alter_column("companies", "timezone", server_default=None)
    op.alter_column("companies", "locale", server_default=None)
    op.alter_column("companies", "work_order_prefix", server_default=None)

    op.add_column(
        "plants",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column(
        "plants",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("job_title", sa.String(length=120)))
    op.add_column("users", sa.Column("phone", sa.String(length=32)))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True)))
    op.add_column("users", sa.Column("password_changed_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "phone")
    op.drop_column("users", "job_title")
    op.drop_column("plants", "updated_at")
    op.drop_column("plants", "created_at")
    op.drop_column("companies", "work_order_prefix")
    op.drop_column("companies", "locale")
    op.drop_column("companies", "timezone")
    op.drop_column("companies", "industry")
    op.drop_index("ix_audit_events_entity_type", table_name="audit_events")
    op.drop_index("ix_audit_events_company_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_company_entity", table_name="audit_events")
    op.drop_index("ix_audit_company_created", table_name="audit_events")
    op.drop_table("audit_events")
