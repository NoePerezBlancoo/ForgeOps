import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import InventoryMovementType
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class InventoryItem(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_inventory_company_code"),
        Index("ix_inventory_company_active", "company_id", "active"),
        CheckConstraint("version >= 1", name="ck_inventory_item_version"),
    )

    code: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False, default="ud")
    location: Mapped[str | None] = mapped_column(String(160))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    __mapper_args__ = {"version_id_col": version}


class InventoryMovement(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index("ix_inventory_movements_company_created", "company_id", "created_at"),
        Index("ix_inventory_movements_work_order_created", "work_order_id", "created_at"),
        Index("ix_inventory_movements_reversal", "reversal_of_id"),
        CheckConstraint("quantity <> 0", name="ck_inventory_movement_quantity"),
        CheckConstraint("unit_cost >= 0", name="ck_inventory_movement_unit_cost"),
        CheckConstraint(
            "(movement_type = 'RETURN') = (reversal_of_id IS NOT NULL)",
            name="ck_inventory_movement_return_source",
        ),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_orders.id", ondelete="SET NULL")
    )
    reversal_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id", ondelete="SET NULL")
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        Enum(
            InventoryMovementType,
            name="inventory_movement_type",
            native_enum=False,
            length=20,
        ),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    resulting_stock: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    item: Mapped[InventoryItem] = relationship(back_populates="movements")
    user: Mapped["User"] = relationship()  # noqa: F821
    work_order: Mapped["WorkOrder | None"] = relationship(  # noqa: F821
        back_populates="inventory_movements"
    )
    reversal_of: Mapped["InventoryMovement | None"] = relationship(
        remote_side="InventoryMovement.id",
        foreign_keys=[reversal_of_id],
    )
