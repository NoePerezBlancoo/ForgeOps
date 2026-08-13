"""protect inventory history

Revision ID: f4b8d2e6a913
Revises: d3f1a7c9e624
Create Date: 2026-08-13 20:14:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f4b8d2e6a913"
down_revision: str | None = "d3f1a7c9e624"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION forgeops_protect_inventory_history()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF current_setting('app.access_mode', true) = 'system' THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'inventory movement history is immutable';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER inventory_movements_immutable
        BEFORE UPDATE OR DELETE ON inventory_movements
        FOR EACH ROW EXECUTE FUNCTION forgeops_protect_inventory_history()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS inventory_movements_immutable ON inventory_movements"
    )
    op.execute("DROP FUNCTION IF EXISTS forgeops_protect_inventory_history()")
