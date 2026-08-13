import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.core.enums import UserRole
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin

InvitationStatus = Literal["PENDING", "ACCEPTED", "EXPIRED", "REVOKED"]


class UserInvitation(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "user_invitations"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
        Index(
            "ix_user_invitations_company_email_created",
            "company_id",
            "email",
            "created_at",
        ),
        Index("ix_user_invitations_expires_at", "expires_at"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="invitation_user_role", native_enum=False, length=32),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    inviter_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    accepted_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    inviter: Mapped["User | None"] = relationship(foreign_keys=[inviter_id])  # noqa: F821
    accepted_user: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[accepted_user_id]
    )

    @validates("email")
    def normalize_email(self, key: str, value: str) -> str:
        return value.strip().lower()

    @property
    def status(self) -> InvitationStatus:
        if self.revoked_at:
            return "REVOKED"
        if self.accepted_at:
            return "ACCEPTED"
        if _utc(self.expires_at) <= datetime.now(UTC):
            return "EXPIRED"
        return "PENDING"


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
