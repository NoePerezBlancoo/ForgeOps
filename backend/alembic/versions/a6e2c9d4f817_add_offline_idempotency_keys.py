"""add offline idempotency keys

Revision ID: a6e2c9d4f817
Revises: f4b8d2e6a913
Create Date: 2026-08-13 20:28:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a6e2c9d4f817"
down_revision: str | None = "f4b8d2e6a913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("client_request_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_incident_client_request",
        "incidents",
        ["company_id", "reported_by", "client_request_id"],
    )
    op.add_column(
        "work_order_notes", sa.Column("client_request_id", sa.Uuid(), nullable=True)
    )
    op.create_unique_constraint(
        "uq_work_order_note_client_request",
        "work_order_notes",
        ["company_id", "work_order_id", "author_id", "client_request_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_work_order_note_client_request", "work_order_notes", type_="unique"
    )
    op.drop_column("work_order_notes", "client_request_id")
    op.drop_constraint("uq_incident_client_request", "incidents", type_="unique")
    op.drop_column("incidents", "client_request_id")
