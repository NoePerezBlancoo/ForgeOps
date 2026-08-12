from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.enums import CompanyModule, CompanyPlan, SubscriptionStatus
from app.core.schemas import ORMModel


class CompanySummary(ORMModel):
    id: UUID
    name: str
    plan: CompanyPlan
    subscription_status: SubscriptionStatus
    access_status: str
    trial_ends_at: datetime | None
    trial_days_remaining: int | None
    write_enabled: bool
    enabled_modules: list[CompanyModule]


class CompanyRead(CompanySummary):
    tax_id: str | None
    address: str | None
    phone: str | None
    email: str | None
    industry: str | None
    timezone: str
    locale: str
    work_order_prefix: str
    trial_started_at: datetime | None
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


class CompanyModulesUpdate(BaseModel):
    enabled_modules: list[CompanyModule]

    @model_validator(mode="after")
    def validate_dependencies(self):
        selected = set(self.enabled_modules)
        if CompanyModule.KNOWLEDGE in selected:
            selected.add(CompanyModule.DOCUMENTS)
        self.enabled_modules = [module for module in CompanyModule if module in selected]
        return self
