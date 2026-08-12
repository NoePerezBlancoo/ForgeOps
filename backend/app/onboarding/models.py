import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.mixins import TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin


class OnboardingProgress(UUIDPrimaryKeyMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "onboarding_progress"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_onboarding_progress_user"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_steps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    tour_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
