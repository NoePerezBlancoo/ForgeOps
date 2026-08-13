import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class ChecklistTemplate(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "checklist_templates"
    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_checklist_template_company_name"),
        Index("ix_checklist_template_company_active", "company_id", "active"),
    )

    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    items: Mapped[list["ChecklistTemplateItem"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ChecklistTemplateItem.position",
        passive_deletes=True,
    )


class ChecklistTemplateItem(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "checklist_template_items"
    __table_args__ = (
        UniqueConstraint(
            "template_id", "position", name="uq_checklist_template_item_template_position"
        ),
        CheckConstraint("position >= 1", name="ck_checklist_template_item_position"),
    )

    template_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="items")


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
    checklist_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("checklist_templates.id", ondelete="SET NULL"), index=True
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
    checklist_template: Mapped[ChecklistTemplate | None] = relationship()
    work_orders: Mapped[list["WorkOrder"]] = relationship(  # noqa: F821
        back_populates="preventive_plan"
    )
