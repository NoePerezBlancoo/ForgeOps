import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


ActorType = Literal["user", "operator"]


def create_access_token(
    subject_id: uuid.UUID,
    actor_type: ActorType = "user",
    expires_minutes: int | None = None,
) -> str:
    return _create_token(
        subject=subject_id,
        token_type="access",
        actor_type=actor_type,
        expires_delta=timedelta(minutes=expires_minutes or settings.access_token_minutes),
    )


def create_refresh_token(
    subject_id: uuid.UUID,
    actor_type: ActorType = "user",
    expires_delta: timedelta | None = None,
) -> tuple[str, datetime]:
    expires_delta = expires_delta or timedelta(days=settings.refresh_token_days)
    expires_at = datetime.now(UTC) + expires_delta
    return _create_token(subject_id, "refresh", actor_type, expires_delta), expires_at


def _create_token(
    subject: uuid.UUID,
    token_type: str,
    actor_type: ActorType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "actor": actor_type,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except InvalidTokenError as exc:
        raise ValueError("Token invalido o caducado") from exc
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise ValueError("Tipo de token invalido")
    return payload


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
