import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.notifications.models import Notification


def create_notification(
    db: Session,
    *,
    company_id: uuid.UUID,
    recipient_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    href: str | None = None,
    dedupe_key: str | None = None,
) -> Notification:
    if dedupe_key:
        existing = db.scalar(
            select(Notification).where(
                Notification.company_id == company_id,
                Notification.recipient_id == recipient_id,
                Notification.dedupe_key == dedupe_key,
            )
        )
        if existing:
            return existing
    notification = Notification(
        id=uuid.uuid4(),
        company_id=company_id,
        recipient_id=recipient_id,
        type=notification_type,
        title=title[:160],
        body=body[:500],
        href=href[:500] if href else None,
        dedupe_key=dedupe_key[:255] if dedupe_key else None,
    )
    db.add(notification)
    return notification


def list_notifications(
    db: Session,
    company_id: uuid.UUID,
    recipient_id: uuid.UUID,
    *,
    limit: int,
    unread_only: bool,
) -> tuple[list[Notification], int, int]:
    criteria = (
        Notification.company_id == company_id,
        Notification.recipient_id == recipient_id,
    )
    query = select(Notification).where(*criteria)
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    items = list(
        db.scalars(query.order_by(Notification.created_at.desc()).limit(limit))
    )
    total = db.scalar(select(func.count(Notification.id)).where(*criteria)) or 0
    unread = db.scalar(
        select(func.count(Notification.id)).where(
            *criteria,
            Notification.read_at.is_(None),
        )
    ) or 0
    return items, total, unread


def mark_notification_read(
    db: Session,
    company_id: uuid.UUID,
    recipient_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> Notification:
    notification = db.scalar(
        select(Notification)
        .where(
            Notification.id == notification_id,
            Notification.company_id == company_id,
            Notification.recipient_id == recipient_id,
        )
        .with_for_update()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notificacion no encontrada")
    if not notification.read_at:
        notification.read_at = datetime.now(UTC)
        db.commit()
    return notification


def mark_all_notifications_read(
    db: Session,
    company_id: uuid.UUID,
    recipient_id: uuid.UUID,
) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.company_id == company_id,
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    updated = result.rowcount or 0
    db.commit()
    return updated
