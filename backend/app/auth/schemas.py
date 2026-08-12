from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.users.schemas import UserPasswordChange, UserRead


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Correo electronico no valido")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class SessionRead(BaseModel):
    id: UUID
    created_at: datetime
    expires_at: datetime
    current: bool = False


class SessionsRevokedRead(BaseModel):
    revoked: int


__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "SessionRead",
    "SessionsRevokedRead",
    "TokenResponse",
    "UserPasswordChange",
]
