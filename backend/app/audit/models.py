import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TenantMixin, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, TenantMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_company_created", "company_id", "created_at"),
        Index("ix_audit_company_entity", "company_id", "entity_type", "entity_id"),
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None]
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actor: Mapped["User | None"] = relationship()  # noqa: F821
