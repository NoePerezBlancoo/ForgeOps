from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.users.schemas import (
    UserPasswordChange,
    UserRead,
    validate_email,
    validate_password,
)


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


class TrialRegistration(BaseModel):
    company_name: str = Field(min_length=2, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    plant_name: str = Field(min_length=2, max_length=160)
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)
    sample_data: bool = True
    terms_accepted: Literal[True]

    _normalize_email = field_validator("email")(validate_email)
    _password_policy = field_validator("password")(validate_password)

    @field_validator("company_name", "industry", "plant_name", "full_name")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value else None


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


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)

    _normalize_email = field_validator("email")(validate_email)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    password: str = Field(min_length=10, max_length=128)

    _password_policy = field_validator("password")(validate_password)


__all__ = [
    "LoginRequest",
    "PasswordResetConfirm",
    "PasswordResetRequest",
    "RefreshRequest",
    "SessionRead",
    "SessionsRevokedRead",
    "TokenResponse",
    "TrialRegistration",
    "UserPasswordChange",
]
