from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.audit.schemas import AuditEventRead, AuditSummaryRead
from app.audit.service import audit_summary, list_audit_events
from app.auth.dependencies import require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.users.models import User

router = APIRouter(prefix="/audit-events", tags=["Auditoria"])
auditors = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)


@router.get("", response_model=list[AuditEventRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    action: str | None = Query(default=None, max_length=40),
    entity_type: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(auditors),
):
    return list_audit_events(
        db, current_user.company_id, search, action, entity_type, limit
    )


@router.get("/summary", response_model=AuditSummaryRead)
def summary(
    db: Session = Depends(get_db), current_user: User = Depends(auditors)
) -> AuditSummaryRead:
    return audit_summary(db, current_user.company_id)
