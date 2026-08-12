from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.plants.models import Plant
from app.plants.schemas import PlantRead
from app.users.models import User

router = APIRouter(prefix="/plants", tags=["Plantas"])


@router.get("", response_model=list[PlantRead])
def list_plants(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[Plant]:
    return list(
        db.scalars(
            select(Plant)
            .where(Plant.company_id == current_user.company_id, Plant.active.is_(True))
            .order_by(Plant.name)
        )
    )
