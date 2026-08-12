import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.inventory.schemas import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    InventoryMovementRead,
    StockMovementCreate,
)
from app.inventory.service import (
    create_item,
    get_item,
    list_items,
    list_movements,
    register_movement,
    update_item,
)
from app.users.models import User

router = APIRouter(prefix="/inventory", tags=["Inventario"])
managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


@router.get("", response_model=list[InventoryItemRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    low_stock: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_items(db, current_user.company_id, search, low_stock)


@router.get("/{item_id}", response_model=InventoryItemRead)
def show(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_item(db, current_user.company_id, item_id)


@router.post("", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return create_item(db, current_user, payload)


@router.patch("/{item_id}", response_model=InventoryItemRead)
def update(
    item_id: uuid.UUID,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return update_item(db, current_user, item_id, payload)


@router.post("/{item_id}/movements", response_model=InventoryMovementRead)
def movement(
    item_id: uuid.UUID,
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return register_movement(db, current_user, item_id, payload)


@router.get("/{item_id}/movements", response_model=list[InventoryMovementRead])
def movements(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_movements(db, current_user.company_id, item_id)
