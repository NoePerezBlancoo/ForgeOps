import uuid
from datetime import UTC, datetime
from enum import IntEnum

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.dashboard.schemas import DashboardRead
from app.dashboard.service import dashboard_csv, dashboard_data
from app.users.models import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class ReportPeriod(IntEnum):
    WEEK = 7
    MONTH = 30
    QUARTER = 90
    YEAR = 365


@router.get("", response_model=DashboardRead)
def index(
    plant_id: uuid.UUID | None = None,
    period_days: ReportPeriod = ReportPeriod.MONTH,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardRead:
    return dashboard_data(db, current_user.company_id, plant_id, int(period_days))


@router.get("/export")
def export(
    plant_id: uuid.UUID | None = None,
    period_days: ReportPeriod = ReportPeriod.MONTH,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    data = dashboard_data(db, current_user.company_id, plant_id, int(period_days))
    filename = f"forgeops-operaciones-{datetime.now(UTC).date().isoformat()}.csv"
    return Response(
        dashboard_csv(data),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
