import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.notifications.models import Notification
from app.notifications.schemas import (
    NotificationList,
    NotificationMarkAllRead,
    NotificationRead,
    NotificationUnreadCount,
)
from app.notifications.service import (
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.users.models import User

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


@router.get("", response_model=NotificationList)
def index(
    limit: int = Query(default=30, ge=1, le=100),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationList:
    items, total, unread = list_notifications(
        db,
        current_user.company_id,
        current_user.id,
        limit=limit,
        unread_only=unread_only,
    )
    return NotificationList(
        items=[NotificationRead.model_validate(item) for item in items],
        total=total,
        unread=unread,
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationUnreadCount:
    _, _, unread = list_notifications(
        db,
        current_user.company_id,
        current_user.id,
        limit=1,
        unread_only=True,
    )
    return NotificationUnreadCount(unread=unread)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Notification:
    return mark_notification_read(
        db,
        current_user.company_id,
        current_user.id,
        notification_id,
    )


@router.post("/read-all", response_model=NotificationMarkAllRead)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationMarkAllRead:
    return NotificationMarkAllRead(
        updated=mark_all_notifications_read(
            db,
            current_user.company_id,
            current_user.id,
        )
    )
