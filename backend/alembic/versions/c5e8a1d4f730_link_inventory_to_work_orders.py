"""link inventory to work orders

Revision ID: c5e8a1d4f730
Revises: 8a2c4f7d1e90
Create Date: 2026-08-13 19:48:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5e8a1d4f730"
down_revision: str | None = "8a2c4f7d1e90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_check_constraint(
        "ck_inventory_item_version", "inventory_items", "version >= 1"
    )

    op.add_column(
        "inventory_movements", sa.Column("work_order_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "inventory_movements", sa.Column("reversal_of_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "inventory_movements",
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "inventory_movements",
        sa.Column(
            "total_cost",
            sa.Numeric(precision=14, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.execute(
        """
        UPDATE inventory_movements AS movement
        SET unit_cost = COALESCE(item.cost, 0)
        FROM inventory_items AS item
        WHERE item.id = movement.item_id
        """
    )
    op.create_foreign_key(
        "fk_inventory_movements_work_order_id",
        "inventory_movements",
        "work_orders",
        ["work_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_inventory_movements_reversal_of_id",
        "inventory_movements",
        "inventory_movements",
        ["reversal_of_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_inventory_movements_work_order_created",
        "inventory_movements",
        ["work_order_id", "created_at"],
    )
    op.create_index(
        "ix_inventory_movements_reversal",
        "inventory_movements",
        ["reversal_of_id"],
    )
    op.create_check_constraint(
        "ck_inventory_movement_quantity", "inventory_movements", "quantity <> 0"
    )
    op.create_check_constraint(
        "ck_inventory_movement_unit_cost", "inventory_movements", "unit_cost >= 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_inventory_movement_unit_cost", "inventory_movements", type_="check"
    )
    op.drop_constraint(
        "ck_inventory_movement_quantity", "inventory_movements", type_="check"
    )
    op.drop_index("ix_inventory_movements_reversal", table_name="inventory_movements")
    op.drop_index(
        "ix_inventory_movements_work_order_created", table_name="inventory_movements"
    )
    op.drop_constraint(
        "fk_inventory_movements_reversal_of_id",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_inventory_movements_work_order_id",
        "inventory_movements",
        type_="foreignkey",
    )
    op.drop_column("inventory_movements", "total_cost")
    op.drop_column("inventory_movements", "unit_cost")
    op.drop_column("inventory_movements", "reversal_of_id")
    op.drop_column("inventory_movements", "work_order_id")
    op.drop_constraint("ck_inventory_item_version", "inventory_items", type_="check")
    op.drop_column("inventory_items", "version")
