import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_digest,
    verify_password,
)
from app.core.config import settings
from app.operators.models import OperatorAuditEvent, OperatorSession, PlatformOperator
from app.operators.schemas import OperatorPasswordChange
from app.operators.security import verify_mfa_code

DUMMY_OPERATOR_PASSWORD_HASH = hash_password("ForgeOpsTimingCheck123!")


def add_operator_audit_event(
    db: Session,
    operator_id: uuid.UUID | None,
    action: str,
    target_type: str,
    summary: str,
    target_id: uuid.UUID | None = None,
    context: dict | None = None,
    ip_address: str | None = None,
) -> OperatorAuditEvent:
    event = OperatorAuditEvent(
        operator_id=operator_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary[:255],
        context=context or {},
        ip_address=ip_address,
    )
    db.add(event)
    return event


def authenticate_operator(
    db: Session, email: str, password: str, totp_code: str, ip_address: str | None
) -> PlatformOperator:
    operator = db.scalar(
        select(PlatformOperator).where(PlatformOperator.email == email.lower().strip())
    )
    now = datetime.now(UTC)
    if operator and operator.locked_until and _utc(operator.locked_until) > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Acceso bloqueado temporalmente por varios intentos fallidos",
        )
    password_valid = verify_password(
        password,
        operator.password_hash if operator else DUMMY_OPERATOR_PASSWORD_HASH,
    )
    mfa_counter = None
    if operator and operator.mfa_enabled and password_valid:
        try:
            mfa_counter = verify_mfa_code(operator.mfa_secret_encrypted, totp_code)
        except ValueError:
            mfa_counter = None
    credentials_valid = bool(
        operator
        and mfa_counter is not None
        and (operator.last_mfa_counter is None or mfa_counter > operator.last_mfa_counter)
    )
    if not credentials_valid:
        if operator:
            operator.failed_login_attempts += 1
            if operator.failed_login_attempts >= settings.operator_lockout_attempts:
                operator.locked_until = now + timedelta(minutes=settings.operator_lockout_minutes)
                operator.failed_login_attempts = 0
            add_operator_audit_event(
                db,
                operator.id,
                "LOGIN_FAILED",
                "OPERATOR",
                "Intento de acceso de operador fallido",
                operator.id,
                ip_address=ip_address,
            )
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de operador incorrectas",
        )
    if not operator.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operador desactivado")
    operator.failed_login_attempts = 0
    operator.locked_until = None
    operator.last_mfa_counter = mfa_counter
    return operator


def issue_operator_session(
    db: Session, operator: PlatformOperator, ip_address: str | None
) -> tuple[str, str]:
    access_token = create_access_token(
        operator.id,
        actor_type="operator",
        expires_minutes=settings.operator_access_token_minutes,
    )
    refresh_token, expires_at = create_refresh_token(
        operator.id,
        actor_type="operator",
        expires_delta=timedelta(hours=settings.operator_refresh_token_hours),
    )
    db.add(
        OperatorSession(
            operator_id=operator.id,
            token_hash=token_digest(refresh_token),
            expires_at=expires_at,
            ip_address=ip_address,
        )
    )
    operator.last_login_at = datetime.now(UTC)
    add_operator_audit_event(
        db,
        operator.id,
        "LOGIN",
        "OPERATOR",
        "Inicio de sesion en el control de plataforma",
        operator.id,
        ip_address=ip_address,
    )
    db.commit()
    return access_token, refresh_token


def rotate_operator_session(
    db: Session, refresh_token: str, ip_address: str | None
) -> tuple[PlatformOperator, str, str]:
    try:
        payload = decode_token(refresh_token, "refresh")
        if payload.get("actor") != "operator":
            raise ValueError("Tipo de sesion invalido")
        operator_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    session = db.scalar(
        select(OperatorSession)
        .where(OperatorSession.token_hash == token_digest(refresh_token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        not session
        or session.revoked_at
        or _utc(session.expires_at) <= now
        or session.operator_id != operator_id
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion no valida")
    operator = db.scalar(
        select(PlatformOperator).where(
            PlatformOperator.id == operator_id,
            PlatformOperator.active.is_(True),
        )
    )
    if not operator:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta no disponible")

    session.revoked_at = now
    access_token = create_access_token(
        operator.id,
        actor_type="operator",
        expires_minutes=settings.operator_access_token_minutes,
    )
    new_refresh_token, expires_at = create_refresh_token(
        operator.id,
        actor_type="operator",
        expires_delta=timedelta(hours=settings.operator_refresh_token_hours),
    )
    db.add(
        OperatorSession(
            operator_id=operator.id,
            token_hash=token_digest(new_refresh_token),
            expires_at=expires_at,
            ip_address=ip_address,
        )
    )
    db.commit()
    return operator, access_token, new_refresh_token


def revoke_operator_session(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    session = db.scalar(
        select(OperatorSession).where(
            OperatorSession.token_hash == token_digest(refresh_token)
        )
    )
    if session and not session.revoked_at:
        session.revoked_at = datetime.now(UTC)
        db.commit()


def change_operator_password(
    db: Session, operator: PlatformOperator, payload: OperatorPasswordChange
) -> None:
    if not verify_password(payload.current_password, operator.password_hash):
        raise HTTPException(status_code=422, detail="La contrasena actual no es correcta")
    if verify_password(payload.password, operator.password_hash):
        raise HTTPException(status_code=422, detail="La nueva contrasena debe ser diferente")
    operator.password_hash = hash_password(payload.password)
    operator.password_changed_at = datetime.now(UTC)
    db.execute(
        update(OperatorSession)
        .where(
            OperatorSession.operator_id == operator.id,
            OperatorSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    add_operator_audit_event(
        db,
        operator.id,
        "PASSWORD_CHANGE",
        "OPERATOR",
        "Contrasena de operador actualizada",
        operator.id,
    )
    db.commit()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
