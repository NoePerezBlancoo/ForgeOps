import os
import re

from psycopg import sql
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.core.config import settings

ROLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def main() -> None:
    login = os.getenv("DATABASE_RUNTIME_LOGIN", "").strip()
    password = os.getenv("DATABASE_RUNTIME_PASSWORD", "")
    role = login or (settings.database_runtime_role or "").strip()
    if not role:
        print("DATABASE_RUNTIME_ROLE no configurado; se usan credenciales restringidas directas")
        return
    if not ROLE_PATTERN.fullmatch(role):
        raise SystemExit("El rol runtime de PostgreSQL no es valido")
    if login and len(password) < 24:
        raise SystemExit("DATABASE_RUNTIME_PASSWORD debe tener al menos 24 caracteres")
    bootstrap_engine = create_engine(
        settings.migration_database_url or settings.database_url,
        poolclass=NullPool,
    )
    with bootstrap_engine.begin() as connection:
        owner = connection.scalar(text("SELECT current_user"))
        if not ROLE_PATTERN.fullmatch(owner):
            raise SystemExit("El rol propietario de PostgreSQL no es valido")
        exists = connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
        )
        if not exists:
            create_role = sql.SQL(
                "CREATE ROLE {} {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS"
            ).format(
                sql.Identifier(role),
                sql.SQL("LOGIN") if login else sql.SQL("NOLOGIN"),
            )
            connection.exec_driver_sql(
                create_role.as_string(connection.connection.driver_connection)
            )
        if login:
            configure_login = sql.SQL(
                "ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOBYPASSRLS PASSWORD {}"
            ).format(sql.Identifier(role), sql.Literal(password))
            connection.exec_driver_sql(
                configure_login.as_string(connection.connection.driver_connection)
            )
        connection.exec_driver_sql(f'GRANT "{role}" TO "{owner}"')
        connection.exec_driver_sql(f'GRANT USAGE ON SCHEMA public TO "{role}"')
        connection.exec_driver_sql(
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO "{role}"'
        )
        connection.exec_driver_sql(
            f'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO "{role}"'
        )
        connection.exec_driver_sql(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{owner}" IN SCHEMA public '
            f'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "{role}"'
        )
        connection.exec_driver_sql(
            f'ALTER DEFAULT PRIVILEGES FOR ROLE "{owner}" IN SCHEMA public '
            f'GRANT USAGE, SELECT ON SEQUENCES TO "{role}"'
        )
    bootstrap_engine.dispose()
    role_type = "login restringido" if login else "rol restringido"
    print(f"Rol de ejecucion preparado: {role} ({role_type})")


if __name__ == "__main__":
    main()
