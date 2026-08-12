import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.assets.models import Asset
from app.core.enums import Priority, UserRole, WorkOrderStatus
from app.core.pagination import paginate
from app.incidents.models import Incident
from app.users.models import User
from app.work_orders.models import WorkOrder
from app.work_orders.schemas import WorkOrderCreate, WorkOrderUpdate


def _asset_for_company(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.company_id == company_id))
    if not asset:
        raise HTTPException(status_code=422, detail="Activo no valido")
    return asset


def _validate_assignee(db: Session, company_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    if not user_id:
        return
    user = db.scalar(
        select(User).where(User.id == user_id, User.company_id == company_id, User.active.is_(True))
    )
    if not user:
        raise HTTPException(status_code=422, detail="Tecnico no valido")


def _base_query():
    return select(WorkOrder).options(
        joinedload(WorkOrder.asset), joinedload(WorkOrder.assignee), joinedload(WorkOrder.creator)
    )


def list_work_orders(
    db: Session,
    current_user: User,
    search: str | None = None,
    order_status: WorkOrderStatus | None = None,
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
) -> list[WorkOrder]:
    query = _base_query().where(WorkOrder.company_id == current_user.company_id)
    if current_user.role == UserRole.TECHNICIAN:
        query = query.where(WorkOrder.assigned_to == current_user.id)
    if search:
        term = f"%{search.strip()}%"
        query = query.join(WorkOrder.asset).where(
            or_(WorkOrder.number.ilike(term), WorkOrder.title.ilike(term), Asset.code.ilike(term))
        )
    if order_status:
        query = query.where(WorkOrder.status == order_status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if plant_id:
        query = query.where(WorkOrder.plant_id == plant_id)
    return list(db.scalars(query.order_by(WorkOrder.created_at.desc()).limit(500)))


def page_work_orders(
    db: Session,
    current_user: User,
    search: str | None,
    order_status: WorkOrderStatus | None,
    priority: Priority | None,
    plant_id: uuid.UUID | None,
    page: int,
    page_size: int,
    sort: str,
):
    query = _base_query().where(WorkOrder.company_id == current_user.company_id)
    if current_user.role == UserRole.TECHNICIAN:
        query = query.where(WorkOrder.assigned_to == current_user.id)
    if search:
        term = f"%{search.strip()}%"
        query = query.join(WorkOrder.asset).where(
            or_(WorkOrder.number.ilike(term), WorkOrder.title.ilike(term), Asset.code.ilike(term))
        )
    if order_status:
        query = query.where(WorkOrder.status == order_status)
    if priority:
        query = query.where(WorkOrder.priority == priority)
    if plant_id:
        query = query.where(WorkOrder.plant_id == plant_id)
    order_by = {
        "created": WorkOrder.created_at.desc(),
        "scheduled": WorkOrder.scheduled_date.asc().nullslast(),
        "number": WorkOrder.number.desc(),
    }[sort]
    return paginate(
        db,
        query.order_by(order_by),
        page,
        page_size,
        sort,
        {
            "search": search,
            "status": order_status.value if order_status else None,
            "priority": priority.value if priority else None,
            "plant_id": str(plant_id) if plant_id else None,
        },
        unique=True,
    )


def get_work_order(db: Session, current_user: User, order_id: uuid.UUID) -> WorkOrder:
    query = _base_query().where(
        WorkOrder.id == order_id, WorkOrder.company_id == current_user.company_id
    )
    if current_user.role == UserRole.TECHNICIAN:
        query = query.where(WorkOrder.assigned_to == current_user.id)
    order = db.scalar(query)
    if not order:
        raise HTTPException(status_code=404, detail="Orden de trabajo no encontrada")
    return order


def create_work_order(db: Session, current_user: User, payload: WorkOrderCreate) -> WorkOrder:
    asset = _asset_for_company(db, current_user.company_id, payload.asset_id)
    if asset.plant_id != payload.plant_id:
        raise HTTPException(status_code=422, detail="El activo no pertenece a la planta indicada")
    _validate_assignee(db, current_user.company_id, payload.assigned_to)
    if payload.incident_id:
        incident = db.scalar(
            select(Incident).where(
                Incident.id == payload.incident_id,
                Incident.company_id == current_user.company_id,
                Incident.asset_id == payload.asset_id,
            )
        )
        if not incident:
            raise HTTPException(status_code=422, detail="Incidencia vinculada no valida")
    values = payload.model_dump()
    if payload.assigned_to and payload.status == WorkOrderStatus.OPEN:
        values["status"] = WorkOrderStatus.ASSIGNED
    prefix = current_user.company.work_order_prefix
    number = f"{prefix}-{datetime.now(UTC):%y%m}-{uuid.uuid4().hex[:6].upper()}"
    order = WorkOrder(
        company_id=current_user.company_id,
        created_by=current_user.id,
        number=number,
        **values,
    )
    db.add(order)
    db.commit()
    return get_work_order(db, current_user, order.id)


def update_work_order(
    db: Session,
    current_user: User,
    order_id: uuid.UUID,
    payload: WorkOrderUpdate,
) -> WorkOrder:
    order = get_work_order(db, current_user, order_id)
    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        _validate_assignee(db, current_user.company_id, changes["assigned_to"])
    if current_user.role == UserRole.TECHNICIAN:
        allowed = {"status", "real_duration", "observations"}
        if set(changes) - allowed:
            raise HTTPException(
                status_code=403, detail="El tecnico solo puede actualizar la ejecucion"
            )
    now = datetime.now(UTC)
    next_status = changes.get("status")
    if next_status == WorkOrderStatus.IN_PROGRESS and not order.started_at:
        order.started_at = now
    if next_status == WorkOrderStatus.COMPLETED:
        order.completed_at = now
    elif next_status and order.status == WorkOrderStatus.COMPLETED:
        order.completed_at = None
    for field, value in changes.items():
        setattr(order, field, value)
    db.commit()
    return get_work_order(db, current_user, order.id)
