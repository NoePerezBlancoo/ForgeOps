import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.audit.models import AuditEvent
from app.audit.schemas import AuditSummaryRead
from app.auth.models import RefreshSession
from app.core.enums import UserRole
from app.users.models import User


def add_audit_event(
    db: Session,
    company_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    summary: str,
    entity_id: uuid.UUID | None = None,
    context: dict | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        company_id=company_id,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:255],
        context=context or {},
        ip_address=ip_address,
    )
    db.add(event)
    return event


def list_audit_events(
    db: Session,
    company_id: uuid.UUID,
    search: str | None,
    action: str | None,
    entity_type: str | None,
    limit: int,
) -> list[AuditEvent]:
    query = (
        select(AuditEvent)
        .options(joinedload(AuditEvent.actor))
        .where(AuditEvent.company_id == company_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(AuditEvent.summary.ilike(term), AuditEvent.entity_type.ilike(term))
        )
    if action:
        query = query.where(AuditEvent.action == action.upper())
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type.upper())
    return list(db.scalars(query).unique())


def audit_summary(db: Session, company_id: uuid.UUID) -> AuditSummaryRead:
    now = datetime.now(UTC)
    total_events = db.scalar(
        select(func.count(AuditEvent.id)).where(AuditEvent.company_id == company_id)
    )
    last_event_at = db.scalar(
        select(func.max(AuditEvent.created_at)).where(AuditEvent.company_id == company_id)
    )
    active_sessions = db.scalar(
        select(func.count(RefreshSession.id))
        .join(User, User.id == RefreshSession.user_id)
        .where(
            User.company_id == company_id,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > now,
        )
    )
    administrators = db.scalar(
        select(func.count(User.id)).where(
            User.company_id == company_id,
            User.active.is_(True),
            User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN]),
        )
    )
    return AuditSummaryRead(
        total_events=total_events or 0,
        active_sessions=active_sessions or 0,
        administrators=administrators or 0,
        last_event_at=last_event_at,
    )
