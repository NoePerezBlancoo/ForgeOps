"""add plan limits and feature overrides

Revision ID: e61a73c9b204
Revises: d4f82a19e761
Create Date: 2026-08-12 22:55:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e61a73c9b204"
down_revision: str | None = "d4f82a19e761"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("limit_overrides", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    op.add_column(
        "companies",
        sa.Column("feature_overrides", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
    )
    op.alter_column("companies", "limit_overrides", server_default=None)
    op.alter_column("companies", "feature_overrides", server_default=None)


def downgrade() -> None:
    op.drop_column("companies", "feature_overrides")
    op.drop_column("companies", "limit_overrides")
