import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_module, require_roles
from app.core.database import get_db
from app.core.enums import CompanyModule, UserRole
from app.maintenance.schemas import (
    ChecklistTemplateCreate,
    ChecklistTemplateRead,
    ChecklistTemplateUpdate,
    GenerationSummary,
    PreventivePlanCreate,
    PreventivePlanRead,
    PreventivePlanUpdate,
)
from app.maintenance.service import (
    create_checklist_template,
    create_plan,
    generate_due_work_orders,
    generate_work_order,
    get_checklist_template,
    get_plan,
    list_checklist_templates,
    list_plans,
    update_checklist_template,
    update_plan,
)
from app.users.models import User
from app.work_orders.schemas import WorkOrderRead

router = APIRouter(
    prefix="/preventive-maintenance",
    tags=["Mantenimiento preventivo"],
    dependencies=[Depends(require_module(CompanyModule.PREVENTIVE))],
)
managers = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MAINTENANCE_MANAGER)


@router.get("/checklists/templates", response_model=list[ChecklistTemplateRead])
def checklist_index(
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_checklist_templates(db, current_user.company_id, active)


@router.get("/checklists/templates/{template_id}", response_model=ChecklistTemplateRead)
def checklist_show(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_checklist_template(db, current_user.company_id, template_id)


@router.post(
    "/checklists/templates",
    response_model=ChecklistTemplateRead,
    status_code=status.HTTP_201_CREATED,
)
def checklist_store(
    payload: ChecklistTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return create_checklist_template(db, current_user.company_id, payload)


@router.patch(
    "/checklists/templates/{template_id}", response_model=ChecklistTemplateRead
)
def checklist_update(
    template_id: uuid.UUID,
    payload: ChecklistTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return update_checklist_template(db, current_user.company_id, template_id, payload)


@router.get("", response_model=list[PreventivePlanRead])
def index(
    active: bool | None = Query(default=None),
    plant_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_plans(db, current_user.company_id, active, plant_id)


@router.get("/{plan_id}", response_model=PreventivePlanRead)
def show(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_plan(db, current_user.company_id, plan_id)


@router.post("", response_model=PreventivePlanRead, status_code=status.HTTP_201_CREATED)
def store(
    payload: PreventivePlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return create_plan(db, current_user.company_id, payload)


@router.patch("/{plan_id}", response_model=PreventivePlanRead)
def update(
    plan_id: uuid.UUID,
    payload: PreventivePlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return update_plan(db, current_user.company_id, plan_id, payload)


@router.post("/{plan_id}/generate-work-order", response_model=WorkOrderRead)
def generate(
    plan_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(managers),
):
    return generate_work_order(db, current_user, plan_id)


@router.post("/actions/generate-due", response_model=GenerationSummary)
def generate_due(
    db: Session = Depends(get_db), current_user: User = Depends(managers)
) -> GenerationSummary:
    generated, skipped = generate_due_work_orders(db, current_user)
    return GenerationSummary(generated=generated, skipped=skipped)
