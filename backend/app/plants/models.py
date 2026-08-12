from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Plant(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "plants"
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_plants_company_code"),)

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    company: Mapped["Company"] = relationship(back_populates="plants")  # noqa: F821
    assets: Mapped[list["Asset"]] = relationship(back_populates="plant")  # noqa: F821
