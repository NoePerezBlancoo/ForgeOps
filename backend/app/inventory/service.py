import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import StaleDataError

from app.core.enums import InventoryMovementType, NotificationType, UserRole
from app.inventory.models import InventoryItem, InventoryMovement
from app.inventory.schemas import InventoryItemCreate, InventoryItemUpdate, StockMovementCreate
from app.notifications.service import create_notification
from app.users.models import User

MANAGER_ROLES = (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


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
                    unit_cost=item.cost or Decimal("0.00"),
                    total_cost=Decimal("0.00"),
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
    values = payload.model_dump(exclude_unset=True)
    expected_version = values.pop("expected_version")
    item = get_item(db, current_user.company_id, item_id)
    if item.version != expected_version:
        raise HTTPException(
            status_code=409,
            detail="El repuesto ha cambiado. Recarga el inventario antes de continuar",
        )
    for field, value in values.items():
        setattr(item, field, value)
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="El repuesto ha cambiado. Recarga el inventario antes de continuar",
        ) from exc
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
    if item.version != payload.expected_version:
        raise HTTPException(
            status_code=409,
            detail="El stock ha cambiado. Recarga el inventario antes de continuar",
        )
    if payload.movement_type == InventoryMovementType.RETURN:
        raise HTTPException(
            status_code=422,
            detail="Las devoluciones se registran desde la orden de trabajo",
        )

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

    previous_stock = Decimal(item.stock)
    item.stock = resulting_stock
    movement = InventoryMovement(
        company_id=current_user.company_id,
        item_id=item.id,
        user_id=current_user.id,
        movement_type=payload.movement_type,
        quantity=delta,
        resulting_stock=resulting_stock,
        unit_cost=item.cost or Decimal("0.00"),
        total_cost=Decimal("0.00"),
        reason=payload.reason.strip(),
    )
    db.add(movement)
    db.flush()
    create_low_stock_notifications(db, item, previous_stock, movement.id)
    db.commit()
    return db.scalar(
        select(InventoryMovement)
        .options(
            joinedload(InventoryMovement.user), joinedload(InventoryMovement.item)
        )
        .where(InventoryMovement.id == movement.id)
    )


def list_movements(
    db: Session, company_id: uuid.UUID, item_id: uuid.UUID
) -> list[InventoryMovement]:
    get_item(db, company_id, item_id)
    return list(
        db.scalars(
            select(InventoryMovement)
            .options(
                joinedload(InventoryMovement.user), joinedload(InventoryMovement.item)
            )
            .where(
                InventoryMovement.company_id == company_id,
                InventoryMovement.item_id == item_id,
            )
            .order_by(InventoryMovement.created_at.desc())
            .limit(100)
        )
    )


def create_low_stock_notifications(
    db: Session,
    item: InventoryItem,
    previous_stock: Decimal,
    movement_id: uuid.UUID,
) -> None:
    minimum = Decimal(item.minimum_stock)
    if previous_stock <= minimum or Decimal(item.stock) > minimum:
        return
    recipients = db.scalars(
        select(User.id).where(
            User.company_id == item.company_id,
            User.active.is_(True),
            User.role.in_(MANAGER_ROLES),
        )
    )
    for recipient_id in recipients:
        create_notification(
            db,
            company_id=item.company_id,
            recipient_id=recipient_id,
            notification_type=NotificationType.LOW_STOCK,
            title=f"Stock bajo: {item.code}",
            body=(
                f"{item.name} queda en {item.stock} {item.unit}; "
                f"el minimo es {item.minimum_stock} {item.unit}."
            ),
            href="/inventory",
            dedupe_key=f"low-stock:{item.id}:{movement_id}:{recipient_id}",
        )
