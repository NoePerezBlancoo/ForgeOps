import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.enums import InventoryMovementType
from app.inventory.models import InventoryItem, InventoryMovement
from app.inventory.schemas import InventoryItemCreate, InventoryItemUpdate, StockMovementCreate
from app.users.models import User


def list_items(
    db: Session,
    company_id: uuid.UUID,
    search: str | None = None,
    low_stock: bool | None = None,
) -> list[InventoryItem]:
    query = select(InventoryItem).where(InventoryItem.company_id == company_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(InventoryItem.code.ilike(term), InventoryItem.name.ilike(term)))
    if low_stock is True:
        query = query.where(InventoryItem.stock <= InventoryItem.minimum_stock)
    return list(db.scalars(query.order_by(InventoryItem.code)))


def get_item(db: Session, company_id: uuid.UUID, item_id: uuid.UUID) -> InventoryItem:
    item = db.scalar(
        select(InventoryItem).where(
            InventoryItem.id == item_id, InventoryItem.company_id == company_id
        )
    )
    if not item:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")
    return item


def create_item(db: Session, current_user: User, payload: InventoryItemCreate) -> InventoryItem:
    values = payload.model_dump()
    initial_stock = values.pop("stock")
    item = InventoryItem(company_id=current_user.company_id, stock=initial_stock, **values)
    db.add(item)
    try:
        db.flush()
        if initial_stock > 0:
            db.add(
                InventoryMovement(
                    company_id=current_user.company_id,
                    item_id=item.id,
                    user_id=current_user.id,
                    movement_type=InventoryMovementType.RECEIPT,
                    quantity=initial_stock,
                    resulting_stock=initial_stock,
                    reason="Stock inicial",
                )
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El codigo del repuesto ya existe") from exc
    return get_item(db, current_user.company_id, item.id)


def update_item(
    db: Session,
    current_user: User,
    item_id: uuid.UUID,
    payload: InventoryItemUpdate,
) -> InventoryItem:
    item = get_item(db, current_user.company_id, item_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El codigo del repuesto ya existe") from exc
    return item


def register_movement(
    db: Session,
    current_user: User,
    item_id: uuid.UUID,
    payload: StockMovementCreate,
) -> InventoryMovement:
    item = db.scalar(
        select(InventoryItem)
        .where(
            InventoryItem.id == item_id,
            InventoryItem.company_id == current_user.company_id,
            InventoryItem.active.is_(True),
        )
        .with_for_update()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Repuesto no encontrado")

    quantity = Decimal(payload.quantity)
    if payload.movement_type == InventoryMovementType.CONSUMPTION:
        delta = -abs(quantity)
    elif payload.movement_type == InventoryMovementType.RECEIPT:
        delta = abs(quantity)
    else:
        delta = quantity
    resulting_stock = Decimal(item.stock) + delta
    if resulting_stock < 0:
        raise HTTPException(status_code=409, detail="Stock insuficiente para el consumo")

    item.stock = resulting_stock
    movement = InventoryMovement(
        company_id=current_user.company_id,
        item_id=item.id,
        user_id=current_user.id,
        movement_type=payload.movement_type,
        quantity=delta,
        resulting_stock=resulting_stock,
        reason=payload.reason.strip(),
    )
    db.add(movement)
    db.commit()
    return db.scalar(
        select(InventoryMovement)
        .options(joinedload(InventoryMovement.user))
        .where(InventoryMovement.id == movement.id)
    )


def list_movements(
    db: Session, company_id: uuid.UUID, item_id: uuid.UUID
) -> list[InventoryMovement]:
    get_item(db, company_id, item_id)
    return list(
        db.scalars(
            select(InventoryMovement)
            .options(joinedload(InventoryMovement.user))
            .where(
                InventoryMovement.company_id == company_id,
                InventoryMovement.item_id == item_id,
            )
            .order_by(InventoryMovement.created_at.desc())
            .limit(100)
        )
    )
