import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import FrequencyType, Priority
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PreventivePlan(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "preventive_plans"
    __table_args__ = (
        UniqueConstraint("company_id", "asset_id", "name", name="uq_preventive_company_asset_name"),
        Index("ix_preventive_company_next", "company_id", "next_execution"),
        Index("ix_preventive_company_active", "company_id", "active"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    frequency_type: Mapped[FrequencyType] = mapped_column(
        Enum(FrequencyType, name="frequency_type", native_enum=False, length=16), nullable=False
    )
    frequency_value: Mapped[int] = mapped_column(Integer, nullable=False)
    next_execution: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_duration: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="preventive_priority", native_enum=False, length=16),
        default=Priority.MEDIUM,
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    asset: Mapped["Asset"] = relationship()  # noqa: F821
    assignee: Mapped["User | None"] = relationship()  # noqa: F821
    work_orders: Mapped[list["WorkOrder"]] = relationship(  # noqa: F821
        back_populates="preventive_plan"
    )
