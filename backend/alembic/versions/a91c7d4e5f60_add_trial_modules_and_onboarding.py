"""add trial modules and onboarding

Revision ID: a91c7d4e5f60
Revises: 8e859f5d3715
Create Date: 2026-08-12 20:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a91c7d4e5f60"
down_revision: str | None = "8e859f5d3715"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODULES_JSON = '["PREVENTIVE", "INVENTORY", "DOCUMENTS", "KNOWLEDGE"]'


def upgrade() -> None:
    op.alter_column("companies", "tax_id", existing_type=sa.String(length=32), nullable=True)
    op.add_column(
        "companies",
        sa.Column(
            "plan",
            sa.String(length=32),
            server_default="PROFESSIONAL",
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column(
            "subscription_status",
            sa.String(length=32),
            server_default="ACTIVE",
            nullable=False,
        ),
    )
    op.add_column(
        "companies",
        sa.Column("trial_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column(
            "enabled_modules",
            sa.JSON(),
            server_default=MODULES_JSON,
            nullable=False,
        ),
    )
    op.create_index(
        "ix_companies_subscription_status",
        "companies",
        ["subscription_status"],
    )
    op.create_index("ix_companies_trial_ends_at", "companies", ["trial_ends_at"])

    op.create_table(
        "onboarding_progress",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("completed_steps", sa.JSON(), nullable=False),
        sa.Column("tour_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_onboarding_progress_user"),
    )
    op.create_index(
        "ix_onboarding_progress_company_id",
        "onboarding_progress",
        ["company_id"],
    )
    op.create_index(
        "ix_onboarding_progress_user_id",
        "onboarding_progress",
        ["user_id"],
    )

    op.alter_column("companies", "plan", server_default=None)
    op.alter_column("companies", "subscription_status", server_default=None)
    op.alter_column("companies", "enabled_modules", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_onboarding_progress_user_id", table_name="onboarding_progress")
    op.drop_index("ix_onboarding_progress_company_id", table_name="onboarding_progress")
    op.drop_table("onboarding_progress")
    op.drop_index("ix_companies_trial_ends_at", table_name="companies")
    op.drop_index("ix_companies_subscription_status", table_name="companies")
    op.drop_column("companies", "enabled_modules")
    op.drop_column("companies", "trial_ends_at")
    op.drop_column("companies", "trial_started_at")
    op.drop_column("companies", "subscription_status")
    op.drop_column("companies", "plan")
    op.execute(
        "UPDATE companies SET tax_id = 'TRIAL-' || CAST(id AS VARCHAR) WHERE tax_id IS NULL"
    )
    op.alter_column("companies", "tax_id", existing_type=sa.String(length=32), nullable=False)
