from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.auth.schemas import RefreshRequest
from app.companies.entitlements import LIMIT_KEYS
from app.core.enums import CompanyModule, CompanyPlan, SubscriptionStatus
from app.core.schemas import ORMModel
from app.users.schemas import UserPasswordChange


class OperatorRead(ORMModel):
    id: UUID
    full_name: str
    email: str
    active: bool
    mfa_enabled: bool
    last_login_at: datetime | None
    password_changed_at: datetime | None
    created_at: datetime


class OperatorTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    operator: OperatorRead


class OperatorAdminSummary(ORMModel):
    id: UUID
    full_name: str
    email: str
    active: bool
    last_login_at: datetime | None


class OperatorCompanySummary(BaseModel):
    id: UUID
    name: str
    email: str | None
    industry: str | None
    plan: CompanyPlan
    subscription_status: SubscriptionStatus
    access_status: str
    trial_started_at: datetime | None
    trial_ends_at: datetime | None
    trial_days_remaining: int | None
    enabled_modules: list[CompanyModule]
    active: bool
    created_at: datetime
    users_count: int
    plants_count: int
    assets_count: int
    open_incidents_count: int
    open_work_orders_count: int
    last_activity_at: datetime | None


class OperatorCompanyPage(BaseModel):
    items: list[OperatorCompanySummary]
    total: int
    page: int
    page_size: int
    pages: int


class OperatorCompanyDetail(OperatorCompanySummary):
    tax_id: str | None
    address: str | None
    phone: str | None
    timezone: str
    locale: str
    work_order_prefix: str
    updated_at: datetime
    administrators: list[OperatorAdminSummary]
    limits: dict[str, int | None]
    usage: dict[str, int]
    limit_overrides: dict[str, int | None]
    feature_overrides: dict[str, bool]


class OperatorDashboardRead(BaseModel):
    total_companies: int
    active_trials: int
    expiring_trials: int
    expired_trials: int
    active_customers: int
    suspended_companies: int
    active_users: int
    total_plants: int
    total_assets: int
    open_incidents: int
    open_work_orders: int
    storage_bytes: int
    queue_depth: int | None
    failed_jobs: int
    service_status: dict[str, str]
    version: str
    environment: str
    commit: str
    module_adoption: dict[CompanyModule, int]
    recent_companies: list[OperatorCompanySummary]


class OperatorCompanyUpdate(BaseModel):
    plan: CompanyPlan | None = None
    subscription_status: SubscriptionStatus | None = None
    active: bool | None = None
    enabled_modules: list[CompanyModule] | None = None
    limit_overrides: dict[str, int | None] | None = None
    feature_overrides: dict[str, bool] | None = None
    reason: str | None = Field(default=None, min_length=5, max_length=500)

    @model_validator(mode="after")
    def validate_modules(self):
        if self.enabled_modules is not None:
            selected = set(self.enabled_modules)
            if CompanyModule.KNOWLEDGE in selected:
                selected.add(CompanyModule.DOCUMENTS)
            self.enabled_modules = [module for module in CompanyModule if module in selected]
        if self.limit_overrides is not None:
            invalid_keys = set(self.limit_overrides) - LIMIT_KEYS
            invalid_values = [
                value
                for value in self.limit_overrides.values()
                if value is not None and (not isinstance(value, int) or value < 0)
            ]
            if invalid_keys or invalid_values:
                raise ValueError("Los limites personalizados no son validos")
        if self.feature_overrides is not None:
            self.feature_overrides = {
                key.strip().upper(): value for key, value in self.feature_overrides.items()
            }
        if (
            self.subscription_status == SubscriptionStatus.SUSPENDED or self.active is False
        ) and not self.reason:
            raise ValueError("Indica el motivo de la suspension o desactivacion")
        return self


class TrialExtensionRequest(BaseModel):
    days: int = Field(ge=1, le=90)
    reason: str = Field(min_length=5, max_length=500)


class OperatorAuditActor(ORMModel):
    id: UUID
    full_name: str
    email: str


class OperatorAuditEventRead(ORMModel):
    id: UUID
    action: str
    target_type: str
    target_id: UUID | None
    summary: str
    context: dict
    ip_address: str | None
    created_at: datetime
    operator: OperatorAuditActor | None


class OperatorAuditPage(BaseModel):
    items: list[OperatorAuditEventRead]
    total: int
    page: int
    page_size: int
    pages: int


class OperatorPasswordChange(UserPasswordChange):
    pass


class OperatorLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=10, max_length=128)
    totp_code: str = Field(pattern=r"^\d{6}$")

    @field_validator("email")
    @classmethod
    def normalize_operator_email(cls, value: str) -> str:
        return value.strip().lower()


__all__ = [
    "OperatorLoginRequest",
    "OperatorPasswordChange",
    "OperatorTokenResponse",
    "RefreshRequest",
]
