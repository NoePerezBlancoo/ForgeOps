import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.assets.schemas import AssetCreate, AssetRead, AssetUpdate
from app.assets.service import create_asset, get_asset, list_assets, update_asset
from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import AssetStatus, Criticality, UserRole
from app.users.models import User

router = APIRouter(prefix="/assets", tags=["Activos"])
asset_managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


@router.get("", response_model=list[AssetRead])
def index(
    search: str | None = Query(default=None, max_length=100),
    asset_status: AssetStatus | None = Query(default=None, alias="status"),
    criticality: Criticality | None = None,
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_assets(db, current_user.company_id, search, asset_status, criticality, plant_id)


@router.get("/{asset_id}", response_model=AssetRead)
def show(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_asset(db, current_user.company_id, asset_id)


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(asset_managers),
):
    return create_asset(db, current_user.company_id, payload)


@router.patch("/{asset_id}", response_model=AssetRead)
def update(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(asset_managers),
):
    return update_asset(db, current_user.company_id, asset_id, payload)
