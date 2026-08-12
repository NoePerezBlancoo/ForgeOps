import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import Priority, UserRole, WorkOrderStatus
from app.users.models import User
from app.work_orders.schemas import WorkOrderCreate, WorkOrderRead, WorkOrderUpdate
from app.work_orders.service import (
    create_work_order,
    get_work_order,
    list_work_orders,
    update_work_order,
)

router = APIRouter(prefix="/work-orders", tags=["Ordenes de trabajo"])
order_creators = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)
order_editors = require_roles(
    UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER, UserRole.TECHNICIAN
)


@router.get("", response_model=list[WorkOrderRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    order_status: WorkOrderStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_work_orders(db, current_user, search, order_status, priority, plant_id)


@router.get("/{order_id}", response_model=WorkOrderRead)
def show(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_work_order(db, current_user, order_id)


@router.post("", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_creators),
):
    return create_work_order(db, current_user, payload)


@router.patch("/{order_id}", response_model=WorkOrderRead)
def update(
    order_id: uuid.UUID,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_editors),
):
    return update_work_order(db, current_user, order_id, payload)
