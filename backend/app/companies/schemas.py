from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.schemas import ORMModel


class CompanyRead(ORMModel):
    id: UUID
    name: str
    tax_id: str
    address: str | None
    phone: str | None
    email: str | None
    industry: str | None
    timezone: str
    locale: str
    work_order_prefix: str
    active: bool
    created_at: datetime
    updated_at: datetime


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    tax_id: str | None = Field(default=None, min_length=3, max_length=32)
    address: str | None = Field(default=None, max_length=1000)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=120)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, pattern=r"^[a-z]{2}-[A-Z]{2}$")
    work_order_prefix: str | None = Field(default=None, min_length=1, max_length=8)

    @field_validator("name", "tax_id", "address", "phone", "email", "industry", "timezone")
    @classmethod
    def strip_values(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("work_order_prefix")
    @classmethod
    def normalize_prefix(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not normalized.isalnum():
            raise ValueError("El prefijo solo puede contener letras y numeros")
        return normalized
