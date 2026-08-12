import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.enums import CompanyPlan
from app.operators.dependencies import get_current_operator
from app.operators.models import PlatformOperator
from app.operators.schemas import (
    OperatorAuditPage,
    OperatorCompanyDetail,
    OperatorCompanyPage,
    OperatorCompanyUpdate,
    OperatorDashboardRead,
    TrialExtensionRequest,
)
from app.operators.service import (
    extend_company_trial,
    get_company_detail,
    list_companies,
    list_operator_audit,
    platform_dashboard,
    update_company_control,
)

router = APIRouter(prefix="/operator", tags=["Control de plataforma"])


@router.get("/dashboard", response_model=OperatorDashboardRead)
def dashboard(
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorDashboardRead:
    return platform_dashboard(db)


@router.get("/companies", response_model=OperatorCompanyPage)
def companies(
    search: str | None = Query(default=None, max_length=120),
    access_status: Literal["TRIAL", "ACTIVE", "SUSPENDED", "EXPIRED", "INACTIVE"]
    | None = None,
    plan: CompanyPlan | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=100),
    sort: Literal["created", "trial_ends", "name"] = "created",
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorCompanyPage:
    return list_companies(db, search, access_status, plan, page, page_size, sort)


@router.get("/companies/{company_id}", response_model=OperatorCompanyDetail)
def company_detail(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorCompanyDetail:
    return get_company_detail(db, company_id)


@router.patch("/companies/{company_id}", response_model=OperatorCompanyDetail)
def company_update(
    company_id: uuid.UUID,
    payload: OperatorCompanyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorCompanyDetail:
    return update_company_control(
        db,
        operator,
        company_id,
        payload,
        request.client.host if request.client else None,
    )


@router.post("/companies/{company_id}/extend-trial", response_model=OperatorCompanyDetail)
def company_extend_trial(
    company_id: uuid.UUID,
    payload: TrialExtensionRequest,
    request: Request,
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorCompanyDetail:
    return extend_company_trial(
        db,
        operator,
        company_id,
        payload.days,
        payload.reason,
        request.client.host if request.client else None,
    )


@router.get("/audit-events", response_model=OperatorAuditPage)
def audit_events(
    search: str | None = Query(default=None, max_length=120),
    action: str | None = Query(default=None, max_length=48),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=5, le=100),
    db: Session = Depends(get_db),
    operator: PlatformOperator = Depends(get_current_operator),
) -> OperatorAuditPage:
    return list_operator_audit(db, search, action, page, page_size)
