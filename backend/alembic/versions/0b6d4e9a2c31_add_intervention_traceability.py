"""add intervention traceability

Revision ID: 0b6d4e9a2c31
Revises: f72c84da3105
Create Date: 2026-08-13 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0b6d4e9a2c31"
down_revision: str | None = "f72c84da3105"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODE = "current_setting('app.access_mode', true)"
COMPANY_ID = "NULLIF(current_setting('app.company_id', true), '')::uuid"


def upgrade() -> None:
    op.add_column("work_orders", sa.Column("work_performed", sa.Text(), nullable=True))
    op.add_column("work_orders", sa.Column("failure_cause", sa.Text(), nullable=True))
    op.add_column("work_orders", sa.Column("root_cause", sa.Text(), nullable=True))
    op.add_column("work_orders", sa.Column("resolution", sa.Text(), nullable=True))
    op.add_column("work_orders", sa.Column("validated_by", sa.Uuid(), nullable=True))
    op.add_column(
        "work_orders", sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("work_orders", sa.Column("closed_by", sa.Uuid(), nullable=True))
    op.add_column("work_orders", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "work_orders",
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "work_orders",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_work_orders_validated_by_users",
        "work_orders",
        "users",
        ["validated_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_work_orders_closed_by_users",
        "work_orders",
        "users",
        ["closed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_work_orders_validated_by", "work_orders", ["validated_by"])
    op.create_index("ix_work_orders_closed_by", "work_orders", ["closed_by"])

    op.create_table(
        "work_order_participants",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=24), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_id", "user_id", name="uq_work_order_participant_user"),
    )
    op.create_index(
        "ix_work_order_participants_company_id", "work_order_participants", ["company_id"]
    )
    op.create_index(
        "ix_work_order_participants_order_active",
        "work_order_participants",
        ["work_order_id", "active"],
    )
    op.create_index(
        "ix_work_order_participants_user_active",
        "work_order_participants",
        ["company_id", "user_id", "active"],
    )

    op.create_table(
        "work_sessions",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_reason", sa.String(length=24), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["work_order_participants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_work_sessions_non_negative_duration",
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at",
            name="ck_work_sessions_valid_interval",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_sessions_company_id", "work_sessions", ["company_id"])
    op.create_index(
        "ix_work_sessions_order_started", "work_sessions", ["work_order_id", "started_at"]
    )
    op.create_index(
        "ix_work_sessions_user_started",
        "work_sessions",
        ["company_id", "user_id", "started_at"],
    )
    op.create_index(
        "uq_work_sessions_open_user_order",
        "work_sessions",
        ["work_order_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.create_table(
        "work_order_notes",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=True),
        sa.Column("note_type", sa.String(length=24), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_work_order_notes_company_id", "work_order_notes", ["company_id"])
    op.create_index(
        "ix_work_order_notes_order_created", "work_order_notes", ["work_order_id", "created_at"]
    )

    op.create_table(
        "work_order_events",
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("work_order_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_order_id", "sequence_no", name="uq_work_order_event_sequence"),
    )
    op.create_index("ix_work_order_events_company_id", "work_order_events", ["company_id"])
    op.create_index(
        "ix_work_order_events_order_sequence",
        "work_order_events",
        ["work_order_id", "sequence_no"],
    )
    op.create_index(
        "ix_work_order_events_company_occurred",
        "work_order_events",
        ["company_id", "occurred_at"],
    )

    for table in (
        "work_order_participants",
        "work_sessions",
        "work_order_notes",
        "work_order_events",
    ):
        _enable_tenant_rls(table)

    op.execute(
        """
        CREATE FUNCTION forgeops_protect_intervention_history()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' AND current_setting('app.access_mode', true) = 'system' THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'intervention history is immutable';
        END;
        $$
        """
    )
    for table in ("work_order_notes", "work_order_events"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION forgeops_protect_intervention_history()
            """
        )

    op.execute("SELECT set_config('app.access_mode', 'system', true)")
    op.execute(
        """
        INSERT INTO work_order_participants (
            id, company_id, work_order_id, user_id, assigned_by, role, active, joined_at
        )
        SELECT
            gen_random_uuid(), company_id, id, assigned_to, created_by, 'LEAD', true, created_at
        FROM work_orders
        WHERE assigned_to IS NOT NULL
        """
    )
    op.execute(
        """
        INSERT INTO work_order_events (
            id, company_id, work_order_id, actor_id, sequence_no,
            event_type, summary, details, occurred_at
        )
        SELECT
            gen_random_uuid(), company_id, id, created_by, 1,
            'CREATED', 'Orden de trabajo creada', '{"migrated": true}'::json, created_at
        FROM work_orders
        """
    )


def downgrade() -> None:
    for table in ("work_order_events", "work_order_notes"):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS forgeops_protect_intervention_history()")

    for table in (
        "work_order_events",
        "work_order_notes",
        "work_sessions",
        "work_order_participants",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_work_order_events_company_occurred", table_name="work_order_events")
    op.drop_index("ix_work_order_events_order_sequence", table_name="work_order_events")
    op.drop_index("ix_work_order_events_company_id", table_name="work_order_events")
    op.drop_table("work_order_events")
    op.drop_index("ix_work_order_notes_order_created", table_name="work_order_notes")
    op.drop_index("ix_work_order_notes_company_id", table_name="work_order_notes")
    op.drop_table("work_order_notes")
    op.drop_index("uq_work_sessions_open_user_order", table_name="work_sessions")
    op.drop_index("ix_work_sessions_user_started", table_name="work_sessions")
    op.drop_index("ix_work_sessions_order_started", table_name="work_sessions")
    op.drop_index("ix_work_sessions_company_id", table_name="work_sessions")
    op.drop_table("work_sessions")
    op.drop_index("ix_work_order_participants_user_active", table_name="work_order_participants")
    op.drop_index("ix_work_order_participants_order_active", table_name="work_order_participants")
    op.drop_index("ix_work_order_participants_company_id", table_name="work_order_participants")
    op.drop_table("work_order_participants")

    op.drop_index("ix_work_orders_closed_by", table_name="work_orders")
    op.drop_index("ix_work_orders_validated_by", table_name="work_orders")
    op.drop_constraint("fk_work_orders_closed_by_users", "work_orders", type_="foreignkey")
    op.drop_constraint("fk_work_orders_validated_by_users", "work_orders", type_="foreignkey")
    op.drop_column("work_orders", "updated_at")
    op.drop_column("work_orders", "version")
    op.drop_column("work_orders", "closed_at")
    op.drop_column("work_orders", "closed_by")
    op.drop_column("work_orders", "validated_at")
    op.drop_column("work_orders", "validated_by")
    op.drop_column("work_orders", "resolution")
    op.drop_column("work_orders", "root_cause")
    op.drop_column("work_orders", "failure_cause")
    op.drop_column("work_orders", "work_performed")


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
        USING (
            {MODE} IN ('platform', 'system')
            OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})
        )
        WITH CHECK (
            {MODE} IN ('platform', 'system')
            OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})
        )
        """
    )
