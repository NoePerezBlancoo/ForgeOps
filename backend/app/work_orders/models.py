import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import Priority, WorkOrderStatus, WorkOrderType
from app.core.mixins import TenantMixin, UUIDPrimaryKeyMixin


class WorkOrder(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_work_orders_company_number"),
        Index("ix_work_orders_company_status", "company_id", "status"),
        Index("ix_work_orders_company_scheduled", "company_id", "scheduled_date"),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="SET NULL"), index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[WorkOrderType] = mapped_column(
        Enum(WorkOrderType, name="work_order_type", native_enum=False, length=24),
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="work_order_priority", native_enum=False, length=16),
        default=Priority.MEDIUM,
        nullable=False,
    )
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus, name="work_order_status", native_enum=False, length=24),
        default=WorkOrderStatus.OPEN,
        nullable=False,
    )
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_duration: Mapped[int | None] = mapped_column(Integer)
    real_duration: Mapped[int | None] = mapped_column(Integer)
    observations: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    asset: Mapped["Asset"] = relationship(back_populates="work_orders")  # noqa: F821
    incident: Mapped["Incident | None"] = relationship(back_populates="work_orders")  # noqa: F821
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assigned_to])  # noqa: F821
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821
