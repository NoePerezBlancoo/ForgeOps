import re

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.core.config import settings

ROLE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def main() -> None:
    role = (settings.database_runtime_role or "").strip()
    if not role:
        print("DATABASE_RUNTIME_ROLE no configurado; se usan credenciales restringidas directas")
        return
    if not ROLE_PATTERN.fullmatch(role):
        raise SystemExit("DATABASE_RUNTIME_ROLE no es valido")
    bootstrap_engine = create_engine(settings.database_url, poolclass=NullPool)
    with bootstrap_engine.begin() as connection:
        owner = connection.scalar(text("SELECT current_user"))
        if not ROLE_PATTERN.fullmatch(owner):
            raise SystemExit("El rol propietario de PostgreSQL no es valido")
        exists = connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role}
        )
        if not exists:
            connection.exec_driver_sql(
                f'CREATE ROLE "{role}" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS'
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
    print(f"Rol de ejecucion preparado: {role}")


if __name__ == "__main__":
    main()
