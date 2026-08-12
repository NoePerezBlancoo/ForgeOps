import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.audit.service import add_audit_event
from app.plants.models import Plant
from app.plants.schemas import PlantCreate, PlantUpdate
from app.users.models import User


def list_plants(db: Session, company_id: uuid.UUID, include_inactive: bool) -> list[Plant]:
    query = select(Plant).where(Plant.company_id == company_id).order_by(Plant.name)
    if not include_inactive:
        query = query.where(Plant.active.is_(True))
    return list(db.scalars(query))


def get_plant(db: Session, company_id: uuid.UUID, plant_id: uuid.UUID) -> Plant:
    plant = db.scalar(
        select(Plant).where(Plant.id == plant_id, Plant.company_id == company_id)
    )
    if not plant:
        raise HTTPException(status_code=404, detail="Planta no encontrada")
    return plant


def create_plant(db: Session, current_user: User, payload: PlantCreate) -> Plant:
    plant = Plant(id=uuid.uuid4(), company_id=current_user.company_id, **payload.model_dump())
    db.add(plant)
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        "CREATE",
        "PLANT",
        f"Planta {plant.code} creada",
        plant.id,
    )
    _commit_unique(db)
    return get_plant(db, current_user.company_id, plant.id)


def update_plant(
    db: Session, current_user: User, plant_id: uuid.UUID, payload: PlantUpdate
) -> Plant:
    plant = get_plant(db, current_user.company_id, plant_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("active") is False and plant.active:
        asset_count = db.scalar(
            select(func.count(Asset.id)).where(
                Asset.company_id == current_user.company_id,
                Asset.plant_id == plant.id,
            )
        )
        if asset_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se puede desactivar una planta con activos asociados",
            )
    for field, value in changes.items():
        setattr(plant, field, value)
    action = "ACTIVATE" if changes.get("active") is True else "UPDATE"
    if changes.get("active") is False:
        action = "DEACTIVATE"
    add_audit_event(
        db,
        current_user.company_id,
        current_user.id,
        action,
        "PLANT",
        f"Planta {plant.code} actualizada",
        plant.id,
        {"fields": sorted(changes)},
    )
    _commit_unique(db)
    return get_plant(db, current_user.company_id, plant.id)


def _commit_unique(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una planta con ese codigo",
        ) from exc
