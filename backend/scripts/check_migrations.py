from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.core.database import engine


def main() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    expected = set(script.get_heads())
    with engine.connect() as connection:
        current = set(MigrationContext.configure(connection).get_current_heads())
    if current != expected:
        raise SystemExit(
            "Esquema incompatible: "
            f"revision actual={sorted(current)}, esperada={sorted(expected)}. "
            "Ejecuta 'alembic upgrade head' como release command."
        )
    print(f"Esquema compatible: {', '.join(sorted(current))}")


if __name__ == "__main__":
    main()
