import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.dashboard.schemas import DashboardRead
from app.dashboard.service import dashboard_data
from app.users.models import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardRead)
def index(
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardRead:
    return dashboard_data(db, current_user.company_id, plant_id)
