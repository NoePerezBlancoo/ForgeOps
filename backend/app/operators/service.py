import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session, joinedload

from app.assets.models import Asset
from app.audit.models import AuditEvent
from app.auth.models import RefreshSession
from app.companies.models import Company
from app.core.config import settings
from app.core.enums import (
    CompanyModule,
    CompanyPlan,
    IncidentStatus,
    SubscriptionStatus,
    UserRole,
    WorkOrderStatus,
)
from app.incidents.models import Incident
from app.operators.auth_service import add_operator_audit_event
from app.operators.models import OperatorAuditEvent, PlatformOperator
from app.operators.schemas import (
    OperatorAdminSummary,
    OperatorAuditPage,
    OperatorCompanyDetail,
    OperatorCompanyPage,
    OperatorCompanySummary,
    OperatorCompanyUpdate,
    OperatorDashboardRead,
)
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder

OPEN_INCIDENT_STATUSES = [
    IncidentStatus.OPEN,
    IncidentStatus.ASSIGNED,
    IncidentStatus.IN_PROGRESS,
    IncidentStatus.WAITING,
]
OPEN_ORDER_STATUSES = [
    WorkOrderStatus.OPEN,
    WorkOrderStatus.ASSIGNED,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.WAITING,
]


def list_companies(
    db: Session,
    search: str | None,
    access_status: str | None,
    plan: CompanyPlan | None,
    page: int,
    page_size: int,
    sort: str,
) -> OperatorCompanyPage:
    filters = _company_filters(search, access_status, plan)
    total = db.scalar(select(func.count(Company.id)).where(*filters)) or 0
    order_by = {
        "created": Company.created_at.desc(),
        "trial_ends": Company.trial_ends_at.asc().nullslast(),
        "name": Company.name.asc(),
    }.get(sort, Company.created_at.desc())
    rows = db.execute(
        _company_summary_query()
        .where(*filters)
        .order_by(order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return OperatorCompanyPage(
        items=[_company_summary(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


def get_company_detail(db: Session, company_id: uuid.UUID) -> OperatorCompanyDetail:
    row = db.execute(
        _company_summary_query().where(Company.id == company_id)
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    summary = _company_summary(row)
    company = row[0]
    admins = db.scalars(
        select(User)
        .where(
            User.company_id == company_id,
            User.role.in_([UserRole.SUPER_ADMIN, UserRole.ADMIN]),
        )
        .order_by(User.active.desc(), User.full_name)
    )
    return OperatorCompanyDetail(
        **summary.model_dump(),
        tax_id=company.tax_id,
        address=company.address,
        phone=company.phone,
        timezone=company.timezone,
        locale=company.locale,
        work_order_prefix=company.work_order_prefix,
        updated_at=company.updated_at,
        administrators=[OperatorAdminSummary.model_validate(admin) for admin in admins],
    )


def update_company_control(
    db: Session,
    operator: PlatformOperator,
    company_id: uuid.UUID,
    payload: OperatorCompanyUpdate,
    ip_address: str | None,
) -> OperatorCompanyDetail:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    changes = payload.model_dump(exclude_unset=True)
    reason = changes.pop("reason", None)
    if not changes:
        return get_company_detail(db, company_id)
    before = {
        "plan": company.plan.value,
        "subscription_status": company.subscription_status.value,
        "active": company.active,
        "enabled_modules": list(company.enabled_modules),
    }
    if "enabled_modules" in changes and changes["enabled_modules"] is not None:
        changes["enabled_modules"] = [module.value for module in changes["enabled_modules"]]
    if changes.get("subscription_status") == SubscriptionStatus.TRIAL:
        changes["plan"] = CompanyPlan.TRIAL
    elif changes.get("subscription_status") == SubscriptionStatus.ACTIVE:
        if changes.get("plan", company.plan) == CompanyPlan.TRIAL:
            changes["plan"] = CompanyPlan.PROFESSIONAL
    elif changes.get("plan") == CompanyPlan.TRIAL:
        changes["subscription_status"] = SubscriptionStatus.TRIAL
    elif changes.get("plan") in {CompanyPlan.DEMO, CompanyPlan.PROFESSIONAL}:
        changes.setdefault("subscription_status", SubscriptionStatus.ACTIVE)
    for field, value in changes.items():
        setattr(company, field, value)
    now = datetime.now(UTC)
    if company.subscription_status == SubscriptionStatus.TRIAL and (
        not company.trial_ends_at or _utc(company.trial_ends_at) <= now
    ):
        company.trial_started_at = company.trial_started_at or now
        company.trial_ends_at = now + timedelta(days=settings.trial_days)
    if company.active is False:
        _revoke_company_sessions(db, company.id)
    after = {
        "plan": company.plan.value,
        "subscription_status": company.subscription_status.value,
        "active": company.active,
        "enabled_modules": list(company.enabled_modules),
    }
    add_operator_audit_event(
        db,
        operator.id,
        "COMPANY_UPDATE",
        "COMPANY",
        f"Configuracion comercial actualizada para {company.name}",
        company.id,
        {"before": before, "after": after, "reason": reason},
        ip_address,
    )
    db.commit()
    return get_company_detail(db, company_id)


def extend_company_trial(
    db: Session,
    operator: PlatformOperator,
    company_id: uuid.UUID,
    days: int,
    reason: str,
    ip_address: str | None,
) -> OperatorCompanyDetail:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    now = datetime.now(UTC)
    previous_end = company.trial_ends_at
    base = max(_utc(previous_end), now) if previous_end else now
    company.plan = CompanyPlan.TRIAL
    company.subscription_status = SubscriptionStatus.TRIAL
    company.trial_started_at = company.trial_started_at or now
    company.trial_ends_at = base + timedelta(days=days)
    company.active = True
    add_operator_audit_event(
        db,
        operator.id,
        "TRIAL_EXTEND",
        "COMPANY",
        f"Prueba de {company.name} ampliada {days} dias",
        company.id,
        {
            "days": days,
            "previous_end": previous_end.isoformat() if previous_end else None,
            "new_end": company.trial_ends_at.isoformat(),
            "reason": reason,
        },
        ip_address,
    )
    db.commit()
    return get_company_detail(db, company_id)


def platform_dashboard(db: Session) -> OperatorDashboardRead:
    now = datetime.now(UTC)
    in_seven_days = now + timedelta(days=7)
    active_company = Company.active.is_(True)
    active_trials = db.scalar(
        select(func.count(Company.id)).where(
            active_company,
            Company.subscription_status == SubscriptionStatus.TRIAL,
            Company.trial_ends_at > now,
        )
    ) or 0
    recent = list_companies(db, None, None, None, 1, 5, "created").items
    modules = {module: 0 for module in CompanyModule}
    enabled_module_rows = db.scalars(select(Company.enabled_modules).where(active_company))
    for enabled in enabled_module_rows:
        for module in CompanyModule:
            if module.value in (enabled or []):
                modules[module] += 1
    return OperatorDashboardRead(
        total_companies=db.scalar(select(func.count(Company.id))) or 0,
        active_trials=active_trials,
        expiring_trials=db.scalar(
            select(func.count(Company.id)).where(
                active_company,
                Company.subscription_status == SubscriptionStatus.TRIAL,
                Company.trial_ends_at > now,
                Company.trial_ends_at <= in_seven_days,
            )
        )
        or 0,
        expired_trials=db.scalar(
            select(func.count(Company.id)).where(*_access_status_filter("EXPIRED"))
        )
        or 0,
        active_customers=db.scalar(
            select(func.count(Company.id)).where(
                active_company,
                Company.subscription_status == SubscriptionStatus.ACTIVE,
            )
        )
        or 0,
        suspended_companies=db.scalar(
            select(func.count(Company.id)).where(
                Company.subscription_status == SubscriptionStatus.SUSPENDED
            )
        )
        or 0,
        active_users=db.scalar(
            select(func.count(User.id))
            .join(Company, Company.id == User.company_id)
            .where(User.active.is_(True), Company.active.is_(True))
        )
        or 0,
        total_assets=db.scalar(select(func.count(Asset.id))) or 0,
        open_incidents=db.scalar(
            select(func.count(Incident.id)).where(Incident.status.in_(OPEN_INCIDENT_STATUSES))
        )
        or 0,
        open_work_orders=db.scalar(
            select(func.count(WorkOrder.id)).where(WorkOrder.status.in_(OPEN_ORDER_STATUSES))
        )
        or 0,
        module_adoption=modules,
        recent_companies=recent,
    )


def list_operator_audit(
    db: Session,
    search: str | None,
    action: str | None,
    page: int,
    page_size: int,
) -> OperatorAuditPage:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(
                OperatorAuditEvent.summary.ilike(term),
                OperatorAuditEvent.target_type.ilike(term),
            )
        )
    if action:
        filters.append(OperatorAuditEvent.action == action.upper())
    total = db.scalar(select(func.count(OperatorAuditEvent.id)).where(*filters)) or 0
    rows = db.scalars(
        select(OperatorAuditEvent)
        .options(joinedload(OperatorAuditEvent.operator))
        .where(*filters)
        .order_by(OperatorAuditEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique()
    return OperatorAuditPage(
        items=list(rows),
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


def _company_summary_query():
    users_count = (
        select(func.count(User.id))
        .where(User.company_id == Company.id, User.active.is_(True))
        .correlate(Company)
        .scalar_subquery()
    )
    plants_count = (
        select(func.count(Plant.id))
        .where(Plant.company_id == Company.id, Plant.active.is_(True))
        .correlate(Company)
        .scalar_subquery()
    )
    assets_count = (
        select(func.count(Asset.id))
        .where(Asset.company_id == Company.id)
        .correlate(Company)
        .scalar_subquery()
    )
    incidents_count = (
        select(func.count(Incident.id))
        .where(
            Incident.company_id == Company.id,
            Incident.status.in_(OPEN_INCIDENT_STATUSES),
        )
        .correlate(Company)
        .scalar_subquery()
    )
    orders_count = (
        select(func.count(WorkOrder.id))
        .where(
            WorkOrder.company_id == Company.id,
            WorkOrder.status.in_(OPEN_ORDER_STATUSES),
        )
        .correlate(Company)
        .scalar_subquery()
    )
    last_activity = (
        select(func.max(AuditEvent.created_at))
        .where(AuditEvent.company_id == Company.id)
        .correlate(Company)
        .scalar_subquery()
    )
    return select(
        Company,
        users_count.label("users_count"),
        plants_count.label("plants_count"),
        assets_count.label("assets_count"),
        incidents_count.label("incidents_count"),
        orders_count.label("orders_count"),
        last_activity.label("last_activity"),
    )


def _company_summary(row) -> OperatorCompanySummary:
    company = row[0]
    return OperatorCompanySummary(
        id=company.id,
        name=company.name,
        email=company.email,
        industry=company.industry,
        plan=company.plan,
        subscription_status=company.subscription_status,
        access_status=company.access_status,
        trial_started_at=company.trial_started_at,
        trial_ends_at=company.trial_ends_at,
        trial_days_remaining=company.trial_days_remaining,
        enabled_modules=company.enabled_modules,
        active=company.active,
        created_at=company.created_at,
        users_count=row.users_count,
        plants_count=row.plants_count,
        assets_count=row.assets_count,
        open_incidents_count=row.incidents_count,
        open_work_orders_count=row.orders_count,
        last_activity_at=row.last_activity,
    )


def _company_filters(
    search: str | None, access_status: str | None, plan: CompanyPlan | None
) -> list:
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(
            or_(Company.name.ilike(term), Company.email.ilike(term), Company.industry.ilike(term))
        )
    if access_status:
        filters.extend(_access_status_filter(access_status))
    if plan:
        filters.append(Company.plan == plan)
    return filters


def _access_status_filter(access_status: str) -> list:
    now = datetime.now(UTC)
    if access_status == "EXPIRED":
        return [
            Company.subscription_status == SubscriptionStatus.TRIAL,
            or_(Company.trial_ends_at.is_(None), Company.trial_ends_at <= now),
        ]
    if access_status == "TRIAL":
        return [
            Company.subscription_status == SubscriptionStatus.TRIAL,
            Company.trial_ends_at > now,
            Company.active.is_(True),
        ]
    if access_status == "INACTIVE":
        return [Company.active.is_(False)]
    return [
        Company.subscription_status == SubscriptionStatus(access_status),
        Company.active.is_(True),
    ]


def _revoke_company_sessions(db: Session, company_id: uuid.UUID) -> None:
    user_ids = select(User.id).where(User.company_id == company_id)
    db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id.in_(user_ids), RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
