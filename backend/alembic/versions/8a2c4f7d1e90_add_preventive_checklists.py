"""add preventive checklists

Revision ID: 8a2c4f7d1e90
Revises: 3f8e1c7a9b42
Create Date: 2026-08-13 19:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "8a2c4f7d1e90"
down_revision: str | None = "3f8e1c7a9b42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODE = "current_setting('app.access_mode', true)"
COMPANY_ID = "NULLIF(current_setting('app.company_id', true), '')::uuid"


def upgrade() -> None:
    op.create_table(
        "checklist_templates",
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "name", name="uq_checklist_template_company_name"
        ),
    )
    op.create_index(
        "ix_checklist_template_company_active",
        "checklist_templates",
        ["company_id", "active"],
    )
    op.create_index(
        "ix_checklist_templates_company_id", "checklist_templates", ["company_id"]
    )

    op.create_table(
        "checklist_template_items",
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("position >= 1", name="ck_checklist_template_item_position"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["checklist_templates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "template_id",
            "position",
            name="uq_checklist_template_item_template_position",
        ),
    )
    op.create_index(
        "ix_checklist_template_items_company_id",
        "checklist_template_items",
        ["company_id"],
    )
    op.create_index(
        "ix_checklist_template_items_template_id",
        "checklist_template_items",
        ["template_id"],
    )

    op.add_column(
        "preventive_plans",
        sa.Column("checklist_template_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_preventive_plans_checklist_template_id",
        "preventive_plans",
        ["checklist_template_id"],
    )
    op.create_foreign_key(
        "fk_preventive_plans_checklist_template_id",
        "preventive_plans",
        "checklist_templates",
        ["checklist_template_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "work_order_checklist_items",
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("source_template_item_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("completed_by", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("position >= 1", name="ck_work_order_checklist_item_position"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_template_item_id"],
            ["checklist_template_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id", "position", name="uq_work_order_checklist_item_position"
        ),
    )
    for column in ("company_id", "work_order_id", "source_template_item_id", "completed_by"):
        op.create_index(
            f"ix_work_order_checklist_items_{column}",
            "work_order_checklist_items",
            [column],
        )
    op.create_index(
        "ix_work_order_checklist_item_completed",
        "work_order_checklist_items",
        ["work_order_id", "completed_at"],
    )
    op.create_index(
        "ix_work_order_checklist_item_order_position",
        "work_order_checklist_items",
        ["work_order_id", "position"],
    )

    for table in (
        "checklist_templates",
        "checklist_template_items",
        "work_order_checklist_items",
    ):
        _enable_tenant_rls(table)


def downgrade() -> None:
    for table in (
        "work_order_checklist_items",
        "checklist_template_items",
        "checklist_templates",
    ):
        for operation in ("select", "insert", "update", "delete"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{operation} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.drop_table("work_order_checklist_items")
    op.drop_constraint(
        "fk_preventive_plans_checklist_template_id",
        "preventive_plans",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_preventive_plans_checklist_template_id", table_name="preventive_plans"
    )
    op.drop_column("preventive_plans", "checklist_template_id")
    op.drop_table("checklist_template_items")
    op.drop_table("checklist_templates")


def _enable_tenant_rls(table: str) -> None:
    tenant_access = (
        f"{MODE} IN ('platform', 'system') "
        f"OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})"
    )
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
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
        f"CREATE POLICY {table}_delete ON {table} FOR DELETE USING ({tenant_access})"
    )
