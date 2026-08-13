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
from app.core.enums import IncidentStatus, Priority
from app.core.mixins import TenantMixin, UUIDPrimaryKeyMixin


class Incident(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_company_status", "company_id", "status"),
        Index("ix_incidents_company_priority", "company_id", "priority"),
        Index("ix_incidents_company_reported", "company_id", "reported_at"),
        UniqueConstraint(
            "company_id",
            "reported_by",
            "client_request_id",
            name="uq_incident_client_request",
        ),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reported_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    client_request_id: Mapped[uuid.UUID | None] = mapped_column()
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[Priority] = mapped_column(
        Enum(Priority, name="incident_priority", native_enum=False, length=16),
        default=Priority.MEDIUM,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, name="incident_status", native_enum=False, length=24),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    downtime_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)

    asset: Mapped["Asset"] = relationship(back_populates="incidents")  # noqa: F821
    reporter: Mapped["User"] = relationship(foreign_keys=[reported_by])  # noqa: F821
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assigned_to])  # noqa: F821
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="incident")  # noqa: F821
