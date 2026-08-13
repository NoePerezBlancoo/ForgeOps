from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import UserRole
from app.core.schemas import ORMModel
from app.users.schemas import validate_email, validate_password

InvitationStatus = Literal["PENDING", "ACCEPTED", "EXPIRED", "REVOKED"]


class UserInvitationCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(min_length=3, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    role: UserRole = UserRole.TECHNICIAN

    _normalize_email = field_validator("email")(validate_email)

    @field_validator("full_name", "job_title", "phone")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class UserInvitationAccept(BaseModel):
    token: str = Field(min_length=32, max_length=200)
    password: str = Field(min_length=10, max_length=128)

    _password_policy = field_validator("password")(validate_password)


class UserInvitationToken(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class UserInvitationRead(ORMModel):
    id: UUID
    company_id: UUID
    email: str
    full_name: str
    job_title: str | None
    phone: str | None
    role: UserRole
    inviter_id: UUID | None
    accepted_user_id: UUID | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    status: InvitationStatus


class UserInvitationPreview(BaseModel):
    company_name: str
    email: str
    full_name: str
    role: UserRole
    expires_at: datetime


class UserInvitationList(BaseModel):
    items: list[UserInvitationRead]
    pending: int
