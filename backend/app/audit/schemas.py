from datetime import datetime
from uuid import UUID

from app.core.schemas import ORMModel


class AuditActorRead(ORMModel):
    id: UUID
    full_name: str
    email: str


class AuditEventRead(ORMModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None
    summary: str
    context: dict
    ip_address: str | None
    created_at: datetime
    actor: AuditActorRead | None


class AuditSummaryRead(ORMModel):
    total_events: int
    active_sessions: int
    administrators: int
    last_event_at: datetime | None
