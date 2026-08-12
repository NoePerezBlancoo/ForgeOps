import os
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.auth.security import hash_password
from app.core.database import SessionLocal, set_database_context
from app.operators.auth_service import add_operator_audit_event
from app.operators.models import PlatformOperator
from app.operators.security import encrypt_mfa_secret, generate_mfa_secret, provisioning_uri
from app.users.schemas import validate_password


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Falta la variable {name}")
    return value


def main() -> None:
    try:
        name = required("OPERATOR_BOOTSTRAP_NAME")
        email = required("OPERATOR_BOOTSTRAP_EMAIL").lower()
        password = validate_password(required("OPERATOR_BOOTSTRAP_PASSWORD"))
        if len(password) < 12:
            raise ValueError("OPERATOR_BOOTSTRAP_PASSWORD debe tener al menos 12 caracteres")
    except (ValueError, TypeError) as exc:
        print(f"Bootstrap de operador cancelado: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    with SessionLocal() as db:
        set_database_context(db, "system")
        existing = db.scalar(select(PlatformOperator).where(PlatformOperator.email == email))
        if existing:
            print(f"El operador {email} ya existe; no se ha modificado su MFA.")
            return
        secret = generate_mfa_secret()
        operator = PlatformOperator(
            full_name=name,
            email=email,
            password_hash=hash_password(password),
            password_changed_at=datetime.now(UTC),
            mfa_secret_encrypted=encrypt_mfa_secret(secret),
            mfa_enabled=True,
            active=True,
        )
        db.add(operator)
        db.flush()
        add_operator_audit_event(
            db,
            operator.id,
            "BOOTSTRAP",
            "OPERATOR",
            "Operador propietario de ForgeOps creado",
            operator.id,
        )
        db.commit()
        print("Operador ForgeOps creado. Registra ahora el segundo factor:")
        print(f"Cuenta: {email}")
        print(f"Clave TOTP: {secret}")
        print(f"URI: {provisioning_uri(secret, email)}")
        print("La clave TOTP no volvera a mostrarse.")


if __name__ == "__main__":
    main()
