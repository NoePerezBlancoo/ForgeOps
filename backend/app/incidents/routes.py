import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import IncidentStatus, Priority, UserRole
from app.core.schemas import Page
from app.incidents.schemas import IncidentCreate, IncidentRead, IncidentUpdate
from app.incidents.service import (
    create_incident,
    get_incident,
    list_incidents,
    page_incidents,
    update_incident,
)
from app.users.models import User

router = APIRouter(prefix="/incidents", tags=["Incidencias"])
incident_creators = require_roles(
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER, UserRole.TECHNICIAN
)


@router.get("", response_model=list[IncidentRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    incident_status: IncidentStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_incidents(
        db, current_user.company_id, search, incident_status, priority, plant_id
    )


@router.get("/page", response_model=Page[IncidentRead])
def paginated_index(
    search: str | None = Query(default=None, max_length=100),
    incident_status: IncidentStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=10, le=100),
    sort: Literal["reported", "priority", "title"] = "reported",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[IncidentRead]:
    return page_incidents(
        db,
        current_user.company_id,
        search,
        incident_status,
        priority,
        plant_id,
        page,
        page_size,
        sort,
    )


@router.get("/{incident_id}", response_model=IncidentRead)
def show(
    incident_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_incident(db, current_user.company_id, incident_id)


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(incident_creators),
):
    return create_incident(db, current_user.company_id, current_user.id, payload)


@router.patch("/{incident_id}", response_model=IncidentRead)
def update(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(incident_creators),
):
    return update_incident(db, current_user, incident_id, payload)
