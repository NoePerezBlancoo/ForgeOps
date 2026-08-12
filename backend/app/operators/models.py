import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PlatformOperator(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "platform_operators"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    mfa_secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_mfa_counter: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    sessions: Mapped[list["OperatorSession"]] = relationship(
        back_populates="operator", cascade="all, delete-orphan"
    )


class OperatorSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operator_sessions"

    operator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("platform_operators.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    operator: Mapped[PlatformOperator] = relationship(back_populates="sessions")


class OperatorAuditEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "operator_audit_events"
    __table_args__ = (
        Index("ix_operator_audit_created", "created_at"),
        Index("ix_operator_audit_target", "target_type", "target_id"),
    )

    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("platform_operators.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    target_id: Mapped[uuid.UUID | None]
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    operator: Mapped[PlatformOperator | None] = relationship()
