"""enforce postgresql tenant rls

Revision ID: f72c84da3105
Revises: e61a73c9b204
Create Date: 2026-08-12 23:20:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f72c84da3105"
down_revision: str | None = "e61a73c9b204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = (
    "audit_events",
    "assets",
    "work_orders",
    "knowledge_chunks",
    "ai_query_logs",
    "preventive_plans",
    "inventory_items",
    "inventory_movements",
    "technical_documents",
    "onboarding_progress",
    "incidents",
    "plants",
    "background_jobs",
)

MODE = "current_setting('app.access_mode', true)"
COMPANY_ID = "NULLIF(current_setting('app.company_id', true), '')::uuid"


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON "{table}"
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

    _enable("companies")
    op.execute(
        f"""
        CREATE POLICY companies_select ON companies FOR SELECT
        USING (
            {MODE} IN ('platform', 'system', 'auth', 'signup')
            OR ({MODE} = 'tenant' AND id = {COMPANY_ID})
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY companies_insert ON companies FOR INSERT
        WITH CHECK ({MODE} IN ('platform', 'system', 'signup'))
        """
    )
    op.execute(
        f"""
        CREATE POLICY companies_update ON companies FOR UPDATE
        USING ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND id = {COMPANY_ID}))
        WITH CHECK ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND id = {COMPANY_ID}))
        """
    )
    op.execute(
        f"CREATE POLICY companies_delete ON companies FOR DELETE USING ({MODE} IN ('platform', 'system'))"
    )

    _enable("users")
    op.execute(
        f"""
        CREATE POLICY users_select ON users FOR SELECT
        USING (
            {MODE} IN ('platform', 'system', 'auth', 'signup')
            OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY users_insert ON users FOR INSERT
        WITH CHECK (
            {MODE} IN ('platform', 'system', 'signup')
            OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID})
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY users_update ON users FOR UPDATE
        USING ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID}))
        WITH CHECK ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID}))
        """
    )
    op.execute(
        f"""
        CREATE POLICY users_delete ON users FOR DELETE
        USING ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND company_id = {COMPANY_ID}))
        """
    )

    _related_table("refresh_sessions", "user_id")
    _related_table("password_reset_tokens", "user_id")


def downgrade() -> None:
    for table in ("password_reset_tokens", "refresh_sessions"):
        _drop_policies(table, ("select", "insert", "update", "delete"))
        _disable(table)
    _drop_policies("users", ("select", "insert", "update", "delete"))
    _disable("users")
    _drop_policies("companies", ("select", "insert", "update", "delete"))
    _disable("companies")
    for table in reversed(TENANT_TABLES):
        op.execute(f'DROP POLICY IF EXISTS {table}_tenant_isolation ON "{table}"')
        _disable(table)


def _related_table(table: str, user_column: str) -> None:
    _enable(table)
    tenant_user = (
        f"EXISTS (SELECT 1 FROM users WHERE users.id = {table}.{user_column} "
        f"AND users.company_id = {COMPANY_ID})"
    )
    op.execute(
        f"""
        CREATE POLICY {table}_select ON {table} FOR SELECT
        USING ({MODE} IN ('platform', 'system', 'auth') OR ({MODE} = 'tenant' AND {tenant_user}))
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table}_insert ON {table} FOR INSERT
        WITH CHECK ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND {tenant_user}))
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table}_update ON {table} FOR UPDATE
        USING ({MODE} IN ('platform', 'system', 'auth') OR ({MODE} = 'tenant' AND {tenant_user}))
        WITH CHECK ({MODE} IN ('platform', 'system', 'auth') OR ({MODE} = 'tenant' AND {tenant_user}))
        """
    )
    op.execute(
        f"""
        CREATE POLICY {table}_delete ON {table} FOR DELETE
        USING ({MODE} IN ('platform', 'system') OR ({MODE} = 'tenant' AND {tenant_user}))
        """
    )


def _enable(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')


def _disable(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
    op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')


def _drop_policies(table: str, actions: tuple[str, ...]) -> None:
    for action in actions:
        op.execute(f'DROP POLICY IF EXISTS {table}_{action} ON "{table}"')
