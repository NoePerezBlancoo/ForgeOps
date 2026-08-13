"""enforce inventory tenant links

Revision ID: d3f1a7c9e624
Revises: c5e8a1d4f730
Create Date: 2026-08-13 20:08:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d3f1a7c9e624"
down_revision: str | None = "c5e8a1d4f730"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_inventory_movement_return_source",
        "inventory_movements",
        "(movement_type = 'RETURN') = (reversal_of_id IS NOT NULL)",
    )
    op.execute(
        """
        CREATE FUNCTION forgeops_validate_inventory_movement_tenant()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM inventory_items
                WHERE id = NEW.item_id AND company_id = NEW.company_id
            ) THEN
                RAISE EXCEPTION 'inventory item belongs to another tenant'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.work_order_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM work_orders
                WHERE id = NEW.work_order_id AND company_id = NEW.company_id
            ) THEN
                RAISE EXCEPTION 'work order belongs to another tenant'
                    USING ERRCODE = '23514';
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM users
                WHERE id = NEW.user_id AND company_id = NEW.company_id
            ) THEN
                RAISE EXCEPTION 'movement author belongs to another tenant'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.reversal_of_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM inventory_movements
                WHERE id = NEW.reversal_of_id
                  AND company_id = NEW.company_id
                  AND item_id = NEW.item_id
                  AND movement_type = 'CONSUMPTION'
                  AND work_order_id = NEW.work_order_id
            ) THEN
                RAISE EXCEPTION 'reversal source is not a matching tenant consumption'
                    USING ERRCODE = '23514';
            END IF;

            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER inventory_movements_tenant_links
        BEFORE INSERT OR UPDATE OF company_id, item_id, user_id, work_order_id,
            reversal_of_id, movement_type
        ON inventory_movements
        FOR EACH ROW EXECUTE FUNCTION forgeops_validate_inventory_movement_tenant()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS inventory_movements_tenant_links ON inventory_movements"
    )
    op.execute("DROP FUNCTION IF EXISTS forgeops_validate_inventory_movement_tenant()")
    op.drop_constraint(
        "ck_inventory_movement_return_source",
        "inventory_movements",
        type_="check",
    )
