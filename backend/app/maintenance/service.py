import calendar
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.assets.models import Asset
from app.core.enums import FrequencyType, WorkOrderStatus, WorkOrderType
from app.maintenance.models import ChecklistTemplate, ChecklistTemplateItem, PreventivePlan
from app.maintenance.schemas import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    PreventivePlanCreate,
    PreventivePlanUpdate,
)
from app.users.models import User
from app.work_orders.models import WorkOrder, WorkOrderChecklistItem
from app.work_orders.service import initialize_work_order_history


def _base_query():
    return select(PreventivePlan).options(
        joinedload(PreventivePlan.asset),
        joinedload(PreventivePlan.assignee),
        joinedload(PreventivePlan.checklist_template).selectinload(ChecklistTemplate.items),
    )


def _template_query():
    return select(ChecklistTemplate).options(selectinload(ChecklistTemplate.items))


def list_checklist_templates(
    db: Session, company_id: uuid.UUID, active: bool | None = None
) -> list[ChecklistTemplate]:
    query = _template_query().where(ChecklistTemplate.company_id == company_id)
    if active is not None:
        query = query.where(ChecklistTemplate.active.is_(active))
    return list(db.scalars(query.order_by(ChecklistTemplate.name)).unique())


def get_checklist_template(
    db: Session, company_id: uuid.UUID, template_id: uuid.UUID
) -> ChecklistTemplate:
    template = db.scalar(
        _template_query().where(
            ChecklistTemplate.id == template_id,
            ChecklistTemplate.company_id == company_id,
        )
    )
    if not template:
        raise HTTPException(status_code=404, detail="Checklist no encontrado")
    return template


def create_checklist_template(
    db: Session, company_id: uuid.UUID, payload: ChecklistTemplateCreate
) -> ChecklistTemplate:
    _validate_item_positions(payload.items)
    template = ChecklistTemplate(
        company_id=company_id,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        active=payload.active,
    )
    template.items = [
        ChecklistTemplateItem(company_id=company_id, **item.model_dump())
        for item in sorted(payload.items, key=lambda item: item.position)
    ]
    db.add(template)
    _commit_template(db)
    return get_checklist_template(db, company_id, template.id)


def update_checklist_template(
    db: Session,
    company_id: uuid.UUID,
    template_id: uuid.UUID,
    payload: ChecklistTemplateUpdate,
) -> ChecklistTemplate:
    template = get_checklist_template(db, company_id, template_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(template, field, value)
    if payload.items is not None:
        _validate_item_positions(payload.items)
        template.items.clear()
        db.flush()
        template.items = [
            ChecklistTemplateItem(company_id=company_id, **item.model_dump())
            for item in sorted(payload.items, key=lambda item: item.position)
        ]
    _commit_template(db)
    return get_checklist_template(db, company_id, template.id)


def _commit_template(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Ya existe un checklist con ese nombre"
        ) from exc


def _validate_item_positions(items) -> None:
    positions = sorted(item.position for item in items)
    if positions != list(range(1, len(items) + 1)):
        raise HTTPException(
            status_code=422,
            detail="Los pasos del checklist deben tener posiciones consecutivas desde 1",
        )


def _validate_asset(db: Session, company_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    asset = db.scalar(select(Asset).where(Asset.id == asset_id, Asset.company_id == company_id))
    if not asset:
        raise HTTPException(status_code=422, detail="Activo no valido")
    return asset


def _validate_assignee(db: Session, company_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    if not user_id:
        return
    user = db.scalar(
        select(User).where(User.id == user_id, User.company_id == company_id, User.active.is_(True))
    )
    if not user:
        raise HTTPException(status_code=422, detail="Responsable no valido")


def _validate_template(
    db: Session, company_id: uuid.UUID, template_id: uuid.UUID | None
) -> None:
    if not template_id:
        return
    template = db.scalar(
        select(ChecklistTemplate.id).where(
            ChecklistTemplate.id == template_id,
            ChecklistTemplate.company_id == company_id,
            ChecklistTemplate.active.is_(True),
        )
    )
    if not template:
        raise HTTPException(status_code=422, detail="Checklist no valido o inactivo")


def list_plans(
    db: Session,
    company_id: uuid.UUID,
    active: bool | None = None,
    plant_id: uuid.UUID | None = None,
) -> list[PreventivePlan]:
    query = _base_query().where(PreventivePlan.company_id == company_id)
    if active is not None:
        query = query.where(PreventivePlan.active.is_(active))
    if plant_id:
        query = query.where(PreventivePlan.asset.has(Asset.plant_id == plant_id))
    return list(db.scalars(query.order_by(PreventivePlan.next_execution, PreventivePlan.name)))


def get_plan(db: Session, company_id: uuid.UUID, plan_id: uuid.UUID) -> PreventivePlan:
    plan = db.scalar(
        _base_query().where(PreventivePlan.id == plan_id, PreventivePlan.company_id == company_id)
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Plan preventivo no encontrado")
    return plan


def create_plan(
    db: Session, company_id: uuid.UUID, payload: PreventivePlanCreate
) -> PreventivePlan:
    _validate_asset(db, company_id, payload.asset_id)
    _validate_assignee(db, company_id, payload.assigned_to)
    _validate_template(db, company_id, payload.checklist_template_id)
    plan = PreventivePlan(company_id=company_id, **payload.model_dump())
    db.add(plan)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un plan con ese nombre para el activo",
        ) from exc
    return get_plan(db, company_id, plan.id)


def update_plan(
    db: Session, company_id: uuid.UUID, plan_id: uuid.UUID, payload: PreventivePlanUpdate
) -> PreventivePlan:
    plan = get_plan(db, company_id, plan_id)
    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to" in changes:
        _validate_assignee(db, company_id, changes["assigned_to"])
    if "checklist_template_id" in changes:
        _validate_template(db, company_id, changes["checklist_template_id"])
    for field, value in changes.items():
        setattr(plan, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El plan preventivo ya existe") from exc
    return get_plan(db, company_id, plan.id)


def _advance(value: datetime, frequency_type: FrequencyType, amount: int) -> datetime:
    if frequency_type == FrequencyType.DAYS:
        return value + timedelta(days=amount)
    if frequency_type == FrequencyType.WEEKS:
        return value + timedelta(weeks=amount)
    months = amount * (12 if frequency_type == FrequencyType.YEARS else 1)
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def generate_work_order(db: Session, current_user: User, plan_id: uuid.UUID) -> WorkOrder:
    locked_plan = db.scalar(
        select(PreventivePlan)
        .where(
            PreventivePlan.id == plan_id,
            PreventivePlan.company_id == current_user.company_id,
        )
        .with_for_update()
    )
    if not locked_plan:
        raise HTTPException(status_code=404, detail="Plan preventivo no encontrado")
    plan = get_plan(db, current_user.company_id, plan_id)
    if not plan.active:
        raise HTTPException(status_code=409, detail="El plan preventivo esta inactivo")
    pending = db.scalar(
        select(WorkOrder).where(
            WorkOrder.preventive_plan_id == plan.id,
            WorkOrder.status.notin_(
                [WorkOrderStatus.COMPLETED, WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]
            ),
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="El plan ya tiene una orden pendiente")

    now = datetime.now(UTC)
    order = WorkOrder(
        company_id=current_user.company_id,
        plant_id=plan.asset.plant_id,
        asset_id=plan.asset_id,
        preventive_plan_id=plan.id,
        assigned_to=plan.assigned_to,
        created_by=current_user.id,
        number=(
            f"{current_user.company.work_order_prefix}-PREV-"
            f"{now:%y%m}-{uuid.uuid4().hex[:6].upper()}"
        ),
        title=plan.name,
        description=plan.description,
        type=WorkOrderType.PREVENTIVE,
        priority=plan.priority,
        status=WorkOrderStatus.ASSIGNED if plan.assigned_to else WorkOrderStatus.OPEN,
        scheduled_date=plan.next_execution,
        estimated_duration=plan.estimated_duration,
    )
    plan.last_generated_at = now
    plan.next_execution = _advance(plan.next_execution, plan.frequency_type, plan.frequency_value)
    db.add(order)
    initialize_work_order_history(db, order, current_user)
    if plan.checklist_template:
        order.checklist_items = [
            WorkOrderChecklistItem(
                company_id=order.company_id,
                source_template_item_id=item.id,
                title=item.title,
                instructions=item.instructions,
                position=item.position,
                required=item.required,
            )
            for item in plan.checklist_template.items
        ]
    db.commit()
    return order


def generate_due_work_orders(db: Session, current_user: User) -> tuple[int, int]:
    due_plans = list(
        db.scalars(
            _base_query().where(
                PreventivePlan.company_id == current_user.company_id,
                PreventivePlan.active.is_(True),
                PreventivePlan.next_execution <= datetime.now(UTC),
            )
        )
    )
    generated = 0
    skipped = 0
    for plan in due_plans:
        try:
            generate_work_order(db, current_user, plan.id)
            generated += 1
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
            skipped += 1
    return generated, skipped
