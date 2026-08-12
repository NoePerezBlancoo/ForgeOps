import uuid
from datetime import date

from sqlalchemy import Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import AssetStatus, Criticality
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Asset(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_assets_company_code"),
        Index("ix_assets_company_status", "company_id", "status"),
        Index("ix_assets_company_criticality", "company_id", "criticality"),
    )

    plant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    serial_number: Mapped[str | None] = mapped_column(String(120))
    installation_date: Mapped[date | None]
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", native_enum=False, length=32),
        default=AssetStatus.ACTIVE,
        nullable=False,
    )
    criticality: Mapped[Criticality] = mapped_column(
        Enum(Criticality, name="asset_criticality", native_enum=False, length=16),
        default=Criticality.MEDIUM,
        nullable=False,
    )
    location: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)

    plant: Mapped["Plant"] = relationship(back_populates="assets")  # noqa: F821
    incidents: Mapped[list["Incident"]] = relationship(back_populates="asset")  # noqa: F821
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="asset")  # noqa: F821
