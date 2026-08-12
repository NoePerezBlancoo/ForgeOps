from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.enums import UserRole
from app.core.schemas import ORMModel


def validate_email(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Correo electronico no valido")
    return normalized


def validate_password(value: str) -> str:
    if not any(character.islower() for character in value):
        raise ValueError("La contrasena debe incluir una minuscula")
    if not any(character.isupper() for character in value):
        raise ValueError("La contrasena debe incluir una mayuscula")
    if not any(character.isdigit() for character in value):
        raise ValueError("La contrasena debe incluir un numero")
    return value


class UserCreate(BaseModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)
    role: UserRole = UserRole.VIEWER
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)

    _normalize_email = field_validator("email")(validate_email)
    _password_policy = field_validator("password")(validate_password)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    role: UserRole | None = None
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    active: bool | None = None

    _normalize_email = field_validator("email")(validate_email)


class UserPasswordReset(BaseModel):
    password: str = Field(min_length=10, max_length=128)

    _password_policy = field_validator("password")(validate_password)


class UserPasswordChange(UserPasswordReset):
    current_password: str = Field(min_length=8, max_length=128)


class CompanySummary(ORMModel):
    id: UUID
    name: str


class UserRead(ORMModel):
    id: UUID
    company_id: UUID
    full_name: str
    email: str
    job_title: str | None
    phone: str | None
    role: UserRole
    active: bool
    last_login_at: datetime | None
    password_changed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    company: CompanySummary


class UserOption(ORMModel):
    id: UUID
    full_name: str
    email: str
    role: UserRole
    active: bool
