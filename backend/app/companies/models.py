from datetime import UTC, datetime
from math import ceil

from sqlalchemy import JSON, Boolean, DateTime, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import CompanyModule, CompanyPlan, SubscriptionStatus
from app.core.mixins import TimestampMixin, UUIDPrimaryKeyMixin

DEFAULT_COMPANY_MODULES = [module.value for module in CompanyModule]


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    tax_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Madrid", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="es-ES", nullable=False)
    work_order_prefix: Mapped[str] = mapped_column(String(8), default="OT", nullable=False)
    plan: Mapped[CompanyPlan] = mapped_column(
        Enum(CompanyPlan, name="company_plan", native_enum=False, length=32),
        default=CompanyPlan.PROFESSIONAL,
        nullable=False,
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(
            SubscriptionStatus,
            name="subscription_status",
            native_enum=False,
            length=32,
        ),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    enabled_modules: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: list(DEFAULT_COMPANY_MODULES),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    users: Mapped[list["User"]] = relationship(back_populates="company")  # noqa: F821
    plants: Mapped[list["Plant"]] = relationship(back_populates="company")  # noqa: F821

    @property
    def access_status(self) -> str:
        if self.subscription_status == SubscriptionStatus.TRIAL:
            if not self.trial_ends_at or self._utc(self.trial_ends_at) <= datetime.now(UTC):
                return "EXPIRED"
        return self.subscription_status.value

    @property
    def trial_days_remaining(self) -> int | None:
        if self.subscription_status != SubscriptionStatus.TRIAL or not self.trial_ends_at:
            return None
        seconds = (self._utc(self.trial_ends_at) - datetime.now(UTC)).total_seconds()
        return max(0, ceil(seconds / 86400))

    @property
    def write_enabled(self) -> bool:
        return self.active and self.access_status in {
            SubscriptionStatus.TRIAL.value,
            SubscriptionStatus.ACTIVE.value,
        }

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
