import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.core.database import get_db
from app.core.enums import UserRole
from app.plants.schemas import PlantCreate, PlantRead, PlantUpdate
from app.plants.service import create_plant, get_plant, list_plants, update_plant
from app.users.models import User

router = APIRouter(prefix="/plants", tags=["Plantas"])
administrators = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)


@router.get("", response_model=list[PlantRead])
def index(
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return list_plants(db, current_user.company_id, include_inactive)


@router.get("/{plant_id}", response_model=PlantRead)
def show(
    plant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_plant(db, current_user.company_id, plant_id)


@router.post("", response_model=PlantRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: PlantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return create_plant(db, current_user, payload)


@router.patch("/{plant_id}", response_model=PlantRead)
def update(
    plant_id: uuid.UUID,
    payload: PlantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(administrators),
):
    return update_plant(db, current_user, plant_id, payload)
