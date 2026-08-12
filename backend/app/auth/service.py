import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.audit.service import add_audit_event
from app.auth.models import PasswordResetToken, RefreshSession
from app.auth.schemas import PasswordResetConfirm
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    token_digest,
    verify_password,
)
from app.core.config import settings
from app.email.service import EmailMessage, message_to_payload
from app.jobs.service import enqueue_job
from app.users.models import User


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(
        select(User).options(joinedload(User.company)).where(User.email == email.lower().strip())
    )
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas"
        )
    if not user.active or not user.company.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta desactivada")
    return user


def issue_session(db: Session, user: User, ip_address: str | None = None) -> tuple[str, str]:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_digest(refresh_token),
            expires_at=expires_at,
        )
    )
    user.last_login_at = datetime.now(UTC)
    add_audit_event(
        db,
        user.company_id,
        user.id,
        "LOGIN",
        "SESSION",
        "Inicio de sesion correcto",
        user.id,
        ip_address=ip_address,
    )
    db.commit()
    return access_token, refresh_token


def rotate_session(db: Session, refresh_token: str) -> tuple[User, str, str]:
    try:
        payload = decode_token(refresh_token, "refresh")
        if payload.get("actor", "user") != "user":
            raise ValueError("Tipo de sesion invalido")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    session = db.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == token_digest(refresh_token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if not session or session.revoked_at or session.expires_at <= now or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesion no valida")

    user = db.scalar(
        select(User)
        .options(joinedload(User.company))
        .where(User.id == user_id, User.active.is_(True))
    )
    if not user or not user.company.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cuenta no disponible")

    session.revoked_at = now
    user.last_login_at = now
    access_token = create_access_token(user.id)
    new_refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_digest(new_refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return user, access_token, new_refresh_token


def revoke_session(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    session = db.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_digest(refresh_token))
    )
    if session and not session.revoked_at:
        session.revoked_at = datetime.now(UTC)
        db.commit()


def token_expires_in() -> int:
    return settings.access_token_minutes * 60


def request_password_reset(
    db: Session, email: str, ip_address: str | None = None
) -> None:
    user = db.scalar(select(User).where(User.email == email.lower().strip(), User.active.is_(True)))
    if not user:
        return
    now = datetime.now(UTC)
    raw_token = secrets.token_urlsafe(48)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_digest(raw_token),
        expires_at=now + timedelta(minutes=30),
        requested_ip=ip_address,
    )
    db.add(reset)
    db.flush()
    frontend_url = settings.frontend_url.split(",")[0].rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={raw_token}"
    message = EmailMessage(
        recipient=user.email,
        subject="Restablece tu acceso a ForgeOps",
        text_body=(
            "Se ha solicitado restablecer tu contrasena de ForgeOps. "
            f"Este enlace caduca en 30 minutos: {reset_url}"
        ),
        html_body=(
            "<p>Se ha solicitado restablecer tu contrasena de ForgeOps.</p>"
            f'<p><a href="{reset_url}">Restablecer contrasena</a></p>'
            "<p>El enlace caduca en 30 minutos.</p>"
        ),
        template="password_reset",
    )
    enqueue_job(
        db,
        "EMAIL_SEND",
        message_to_payload(message),
        idempotency_key=f"password-reset:{reset.id}",
        company_id=user.company_id,
    )


def confirm_password_reset(db: Session, payload: PasswordResetConfirm) -> None:
    now = datetime.now(UTC)
    reset = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == token_digest(payload.token))
        .with_for_update()
    )
    if not reset or reset.used_at or _utc(reset.expires_at) <= now:
        raise HTTPException(status_code=422, detail="El enlace no es valido o ha caducado")
    user = db.scalar(select(User).where(User.id == reset.user_id, User.active.is_(True)))
    if not user:
        raise HTTPException(status_code=422, detail="El enlace no es valido o ha caducado")
    user.password_hash = hash_password(payload.password)
    user.password_changed_at = now
    reset.used_at = now
    active_sessions = db.scalars(
        select(RefreshSession).where(
            RefreshSession.user_id == user.id,
            RefreshSession.revoked_at.is_(None),
        )
    )
    for session in active_sessions:
        session.revoked_at = now
    add_audit_event(
        db,
        user.company_id,
        user.id,
        "PASSWORD_RESET",
        "USER",
        "Contrasena restablecida mediante enlace de un solo uso",
        user.id,
    )
    db.commit()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
