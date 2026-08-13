import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.assets.models import Asset
from app.core.enums import IncidentStatus, NotificationType, Priority, UserRole
from app.core.pagination import paginate
from app.incidents.models import Incident
from app.incidents.schemas import IncidentCreate, IncidentUpdate
from app.notifications.service import create_notification
from app.users.models import User


def _asset_for_company(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.company_id == company_id))
    if not asset:
        raise HTTPException(status_code=422, detail="Activo no valido")
    return asset


def _assignee_for_company(db: Session, company_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    if not user_id:
        return
    user = db.scalar(
        select(User).where(User.id == user_id, User.company_id == company_id, User.active.is_(True))
    )
    if not user:
        raise HTTPException(status_code=422, detail="Tecnico no valido")


def _base_query():
    return select(Incident).options(
        joinedload(Incident.asset), joinedload(Incident.reporter), joinedload(Incident.assignee)
    )


def list_incidents(
    db: Session,
    company_id: uuid.UUID,
    search: str | None = None,
    incident_status: IncidentStatus | None = None,
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
) -> list[Incident]:
    query = (
        _base_query().where(Incident.company_id == company_id).order_by(Incident.reported_at.desc())
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.join(Incident.asset).where(
            or_(
                Incident.title.ilike(term), Incident.description.ilike(term), Asset.code.ilike(term)
            )
        )
    if incident_status:
        query = query.where(Incident.status == incident_status)
    if priority:
        query = query.where(Incident.priority == priority)
    if plant_id:
        query = query.where(Incident.plant_id == plant_id)
    return list(db.scalars(query.limit(500)))


def page_incidents(
    db: Session,
    company_id: uuid.UUID,
    search: str | None,
    incident_status: IncidentStatus | None,
    priority: Priority | None,
    plant_id: uuid.UUID | None,
    page: int,
    page_size: int,
    sort: str,
):
    query = _base_query().where(Incident.company_id == company_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.join(Incident.asset).where(
            or_(
                Incident.title.ilike(term),
                Incident.description.ilike(term),
                Asset.code.ilike(term),
            )
        )
    if incident_status:
        query = query.where(Incident.status == incident_status)
    if priority:
        query = query.where(Incident.priority == priority)
    if plant_id:
        query = query.where(Incident.plant_id == plant_id)
    order_by = {
        "reported": Incident.reported_at.desc(),
        "priority": Incident.priority.desc(),
        "title": Incident.title.asc(),
    }[sort]
    return paginate(
        db,
        query.order_by(order_by),
        page,
        page_size,
        sort,
        {
            "search": search,
            "status": incident_status.value if incident_status else None,
            "priority": priority.value if priority else None,
            "plant_id": str(plant_id) if plant_id else None,
        },
        unique=True,
    )


def get_incident(db: Session, company_id: uuid.UUID, incident_id: uuid.UUID) -> Incident:
    incident = db.scalar(
        _base_query().where(Incident.id == incident_id, Incident.company_id == company_id)
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incident


def create_incident(
    db: Session, company_id: uuid.UUID, reporter_id: uuid.UUID, payload: IncidentCreate
) -> Incident:
    asset = _asset_for_company(db, company_id, payload.asset_id)
    if asset.plant_id != payload.plant_id:
        raise HTTPException(status_code=422, detail="El activo no pertenece a la planta indicada")
    _assignee_for_company(db, company_id, payload.assigned_to)
    values = payload.model_dump()
    if payload.assigned_to and payload.status == IncidentStatus.OPEN:
        values["status"] = IncidentStatus.ASSIGNED
    incident = Incident(company_id=company_id, reported_by=reporter_id, **values)
    db.add(incident)
    db.flush()
    if incident.priority == Priority.CRITICAL:
        recipients = set(
            db.scalars(
                select(User.id).where(
                    User.company_id == company_id,
                    User.active.is_(True),
                    User.role.in_(
                        (
                            UserRole.SUPER_ADMIN,
                            UserRole.ADMIN,
                            UserRole.MAINTENANCE_MANAGER,
                        )
                    ),
                )
            )
        )
        if incident.assigned_to:
            recipients.add(incident.assigned_to)
        for recipient_id in recipients:
            create_notification(
                db,
                company_id=company_id,
                recipient_id=recipient_id,
                notification_type=NotificationType.CRITICAL_INCIDENT,
                title="Incidencia critica registrada",
                body=f"{asset.code}: {incident.title}",
                href=f"/incidents?incident={incident.id}",
                dedupe_key=f"critical-incident:{incident.id}",
            )
    db.commit()
    return get_incident(db, company_id, incident.id)


def update_incident(
    db: Session,
    current_user: User,
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
) -> Incident:
    incident = get_incident(db, current_user.company_id, incident_id)
    if current_user.role == UserRole.TECHNICIAN and incident.assigned_to != current_user.id:
        raise HTTPException(
            status_code=403, detail="Solo puedes gestionar incidencias asignadas a ti"
        )
    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        _assignee_for_company(db, current_user.company_id, changes["assigned_to"])
    now = datetime.now(UTC)
    next_status = changes.get("status")
    if next_status == IncidentStatus.IN_PROGRESS and not incident.started_at:
        incident.started_at = now
    if next_status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        incident.resolved_at = incident.resolved_at or now
    elif next_status and incident.status in {IncidentStatus.RESOLVED, IncidentStatus.CLOSED}:
        incident.resolved_at = None
    for field, value in changes.items():
        setattr(incident, field, value)
    db.commit()
    return get_incident(db, current_user.company_id, incident.id)
