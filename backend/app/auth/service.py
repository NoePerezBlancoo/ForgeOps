import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth.models import RefreshSession
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    token_digest,
    verify_password,
)
from app.core.config import settings
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


def issue_session(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_digest(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return access_token, refresh_token


def rotate_session(db: Session, refresh_token: str) -> tuple[User, str, str]:
    try:
        payload = decode_token(refresh_token, "refresh")
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
