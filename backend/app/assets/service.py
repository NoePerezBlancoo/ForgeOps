import uuid

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.assets.models import Asset
from app.assets.schemas import AssetCreate, AssetUpdate
from app.core.enums import AssetStatus, Criticality
from app.plants.models import Plant


def _plant_for_company(db: Session, company_id: uuid.UUID, plant_id: uuid.UUID) -> Plant:
    plant = db.scalar(
        select(Plant).where(
            Plant.id == plant_id, Plant.company_id == company_id, Plant.active.is_(True)
        )
    )
    if not plant:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Planta no valida"
        )
    return plant


def list_assets(
    db: Session,
    company_id: uuid.UUID,
    search: str | None = None,
    asset_status: AssetStatus | None = None,
    criticality: Criticality | None = None,
    plant_id: uuid.UUID | None = None,
) -> list[Asset]:
    query = (
        select(Asset)
        .options(joinedload(Asset.plant))
        .where(Asset.company_id == company_id)
        .order_by(Asset.code)
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(Asset.code.ilike(term), Asset.name.ilike(term), Asset.location.ilike(term))
        )
    if asset_status:
        query = query.where(Asset.status == asset_status)
    if criticality:
        query = query.where(Asset.criticality == criticality)
    if plant_id:
        query = query.where(Asset.plant_id == plant_id)
    return list(db.scalars(query))


def get_asset(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(
        select(Asset)
        .options(joinedload(Asset.plant))
        .where(Asset.id == asset_id, Asset.company_id == company_id)
    )
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activo no encontrado")
    return asset


def create_asset(db: Session, company_id: uuid.UUID, payload: AssetCreate) -> Asset:
    _plant_for_company(db, company_id, payload.plant_id)
    asset = Asset(company_id=company_id, **payload.model_dump())
    db.add(asset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo del activo ya existe"
        ) from exc
    return get_asset(db, company_id, asset.id)


def update_asset(
    db: Session, company_id: uuid.UUID, asset_id: uuid.UUID, payload: AssetUpdate
) -> Asset:
    asset = get_asset(db, company_id, asset_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("plant_id"):
        _plant_for_company(db, company_id, changes["plant_id"])
    for field, value in changes.items():
        setattr(asset, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El codigo del activo ya existe"
        ) from exc
    return get_asset(db, company_id, asset.id)
