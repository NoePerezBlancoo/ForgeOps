import uuid
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _engine_options() -> dict:
    options: dict = {"pool_pre_ping": True}
    if settings.database_url.startswith("postgresql+"):
        options["connect_args"] = {
            "connect_timeout": settings.database_connect_timeout_seconds,
            "options": f"-c statement_timeout={settings.database_statement_timeout_ms}",
        }
    if settings.database_pool_mode == "pgbouncer":
        options["poolclass"] = NullPool
        if settings.database_url.startswith("postgresql+psycopg"):
            options["connect_args"]["prepare_threshold"] = None
    else:
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )
    return options


engine = create_engine(settings.database_url, **_engine_options())


@event.listens_for(engine, "connect")
def _activate_runtime_role(dbapi_connection, connection_record) -> None:
    role = (settings.database_runtime_role or "").strip()
    if not role:
        return
    if not role.replace("_", "").isalnum():
        raise ValueError("DATABASE_RUNTIME_ROLE no es valido")
    with dbapi_connection.cursor() as cursor:
        cursor.execute(f'SET ROLE "{role}"')


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "after_begin")
def _apply_database_context(session: Session, transaction, connection) -> None:
    if connection.dialect.name != "postgresql":
        return
    mode = session.info.get("access_mode")
    if not mode:
        return
    connection.execute(
        text(
            "SELECT set_config('app.access_mode', :mode, true), "
            "set_config('app.company_id', :company_id, true)"
        ),
        {"mode": mode, "company_id": session.info.get("company_id", "")},
    )


def set_database_context(
    db: Session,
    access_mode: str,
    company_id: uuid.UUID | None = None,
) -> None:
    if access_mode not in {"tenant", "platform", "auth", "signup", "system"}:
        raise ValueError("Contexto de base de datos no valido")
    if access_mode == "tenant" and not company_id:
        raise ValueError("El contexto tenant requiere company_id")
    db.info["access_mode"] = access_mode
    db.info["company_id"] = str(company_id) if company_id else ""
    if db.bind is not None and db.bind.dialect.name == "postgresql" and db.in_transaction():
        db.execute(
            text(
                "SELECT set_config('app.access_mode', :mode, true), "
                "set_config('app.company_id', :company_id, true)"
            ),
            {"mode": access_mode, "company_id": str(company_id) if company_id else ""},
        )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
