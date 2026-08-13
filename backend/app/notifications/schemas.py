from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import NotificationType
from app.core.schemas import ORMModel


class NotificationRead(ORMModel):
    id: UUID
    type: NotificationType
    title: str
    body: str
    href: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    total: int
    unread: int


class NotificationUnreadCount(BaseModel):
    unread: int


class NotificationMarkAllRead(BaseModel):
    updated: int
