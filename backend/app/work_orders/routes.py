import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import Priority, UserRole, WorkOrderStatus
from app.core.schemas import Page
from app.users.models import User
from app.work_orders.schemas import (
    WorkOrderChecklistItemUpdate,
    WorkOrderComplete,
    WorkOrderCreate,
    WorkOrderDetailRead,
    WorkOrderNoteCreate,
    WorkOrderParticipantCreate,
    WorkOrderRead,
    WorkOrderReopen,
    WorkOrderUpdate,
    WorkOrderValidation,
    WorkSessionCommand,
)
from app.work_orders.service import (
    add_note,
    add_participant,
    close_work,
    complete_work,
    create_work_order,
    get_work_order_detail,
    list_work_orders,
    page_work_orders,
    pause_work,
    remove_participant,
    reopen_work,
    start_work,
    update_checklist_item,
    update_work_order,
    validate_work,
)

router = APIRouter(prefix="/work-orders", tags=["Ordenes de trabajo"])
order_managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)
order_actors = require_roles(
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


@router.get("/page", response_model=Page[WorkOrderRead])
def paginated_index(
    search: str | None = Query(default=None, max_length=100),
    order_status: WorkOrderStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    plant_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=10, le=100),
    sort: Literal["created", "scheduled", "number"] = "created",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[WorkOrderRead]:
    return page_work_orders(
        db,
        current_user,
        search,
        order_status,
        priority,
        plant_id,
        page,
        page_size,
        sort,
    )


@router.get("/{order_id}", response_model=WorkOrderDetailRead)
def show(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_work_order_detail(db, current_user, order_id)


@router.post("", response_model=WorkOrderDetailRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: WorkOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return create_work_order(db, current_user, payload)


@router.patch("/{order_id}", response_model=WorkOrderDetailRead)
def update(
    order_id: uuid.UUID,
    payload: WorkOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return update_work_order(db, current_user, order_id, payload)


@router.post("/{order_id}/participants", response_model=WorkOrderDetailRead)
def store_participant(
    order_id: uuid.UUID,
    payload: WorkOrderParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return add_participant(db, current_user, order_id, payload)


@router.delete("/{order_id}/participants/{participant_id}", response_model=WorkOrderDetailRead)
def destroy_participant(
    order_id: uuid.UUID,
    participant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return remove_participant(db, current_user, order_id, participant_id)


@router.post("/{order_id}/start", response_model=WorkOrderDetailRead)
def start(
    order_id: uuid.UUID,
    payload: WorkSessionCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return start_work(db, current_user, order_id, payload)


@router.post("/{order_id}/resume", response_model=WorkOrderDetailRead)
def resume(
    order_id: uuid.UUID,
    payload: WorkSessionCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return start_work(db, current_user, order_id, payload)


@router.post("/{order_id}/pause", response_model=WorkOrderDetailRead)
def pause(
    order_id: uuid.UUID,
    payload: WorkSessionCommand,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return pause_work(db, current_user, order_id, payload)


@router.post("/{order_id}/notes", response_model=WorkOrderDetailRead)
def store_note(
    order_id: uuid.UUID,
    payload: WorkOrderNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return add_note(db, current_user, order_id, payload)


@router.patch("/{order_id}/checklist/{item_id}", response_model=WorkOrderDetailRead)
def update_checklist(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: WorkOrderChecklistItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return update_checklist_item(db, current_user, order_id, item_id, payload)


@router.post("/{order_id}/complete", response_model=WorkOrderDetailRead)
def complete(
    order_id: uuid.UUID,
    payload: WorkOrderComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_actors),
):
    return complete_work(db, current_user, order_id, payload)


@router.post("/{order_id}/validate", response_model=WorkOrderDetailRead)
def validate(
    order_id: uuid.UUID,
    payload: WorkOrderValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return validate_work(db, current_user, order_id, payload)


@router.post("/{order_id}/close", response_model=WorkOrderDetailRead)
def close(
    order_id: uuid.UUID,
    payload: WorkOrderValidation,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return close_work(db, current_user, order_id, payload)


@router.post("/{order_id}/reopen", response_model=WorkOrderDetailRead)
def reopen(
    order_id: uuid.UUID,
    payload: WorkOrderReopen,
    db: Session = Depends(get_db),
    current_user: User = Depends(order_managers),
):
    return reopen_work(db, current_user, order_id, payload)
