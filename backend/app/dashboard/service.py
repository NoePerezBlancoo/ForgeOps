import uuid
from csv import writer
from datetime import UTC, datetime, timedelta
from io import StringIO

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.companies.models import Company
from app.core.enums import (
    AssetStatus,
    CompanyModule,
    IncidentStatus,
    Priority,
    WorkOrderStatus,
)
from app.dashboard.schemas import (
    AssetImpact,
    ChartItem,
    DashboardRead,
    PilotReadiness,
    RecentIncident,
    SetupItem,
    TechnicianLoad,
    UpcomingWorkOrder,
)
from app.documents.models import TechnicalDocument
from app.incidents.models import Incident
from app.inventory.models import InventoryItem
from app.maintenance.models import PreventivePlan
from app.plants.models import Plant
from app.users.models import User
from app.work_orders.models import WorkOrder, WorkOrderParticipant, WorkSession


def dashboard_data(
    db: Session,
    company_id: uuid.UUID,
    plant_id: uuid.UUID | None = None,
    period_days: int = 30,
) -> DashboardRead:
    now = datetime.now(UTC)
    period_start = (now - timedelta(days=period_days - 1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    asset_scope = [Asset.company_id == company_id]
    incident_scope = [Incident.company_id == company_id]
    order_scope = [WorkOrder.company_id == company_id]
    preventive_scope = [PreventivePlan.company_id == company_id]
    if plant_id:
        asset_scope.append(Asset.plant_id == plant_id)
        incident_scope.append(Incident.plant_id == plant_id)
        order_scope.append(WorkOrder.plant_id == plant_id)
        preventive_scope.append(PreventivePlan.asset.has(Asset.plant_id == plant_id))
    readiness = _pilot_readiness(db, company_id)
    asset_counts = dict(
        db.execute(
            select(Asset.status, func.count(Asset.id))
            .where(*asset_scope)
            .group_by(Asset.status)
        ).all()
    )
    incident_counts = dict(
        db.execute(
            select(Incident.status, func.count(Incident.id))
            .where(*incident_scope)
            .group_by(Incident.status)
        ).all()
    )
    priority_counts = dict(
        db.execute(
            select(Incident.priority, func.count(Incident.id))
            .where(
                *incident_scope,
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]),
            )
            .group_by(Incident.priority)
        ).all()
    )
    order_counts = dict(
        db.execute(
            select(WorkOrder.status, func.count(WorkOrder.id))
            .where(*order_scope)
            .group_by(WorkOrder.status)
        ).all()
    )
    downtime_minutes = db.scalar(
        select(func.coalesce(func.sum(Incident.downtime_minutes), 0)).where(
            *incident_scope,
            Incident.reported_at >= period_start,
        )
    )
    upcoming_preventive_count = db.scalar(
        select(func.count(PreventivePlan.id)).where(
            *preventive_scope,
            PreventivePlan.active.is_(True),
            PreventivePlan.next_execution <= now + timedelta(days=30),
        )
    )
    low_stock_items = db.scalar(
        select(func.count(InventoryItem.id)).where(
            InventoryItem.company_id == company_id,
            InventoryItem.active.is_(True),
            InventoryItem.stock <= InventoryItem.minimum_stock,
        )
    )
    recent_rows = db.execute(
        select(Incident, Asset.code)
        .join(Asset, Asset.id == Incident.asset_id)
        .where(*incident_scope)
        .order_by(Incident.reported_at.desc())
        .limit(5)
    ).all()
    upcoming_rows = db.execute(
        select(WorkOrder, Asset.code)
        .join(Asset, Asset.id == WorkOrder.asset_id)
        .where(
            *order_scope,
            WorkOrder.status.notin_(
                [
                    WorkOrderStatus.PENDING_VALIDATION,
                    WorkOrderStatus.COMPLETED,
                    WorkOrderStatus.CLOSED,
                    WorkOrderStatus.CANCELLED,
                ]
            ),
        )
        .order_by(WorkOrder.scheduled_date.asc().nullslast(), WorkOrder.created_at.desc())
        .limit(5)
    ).all()
    overdue_work_orders = db.scalar(
        select(func.count(WorkOrder.id)).where(
            *order_scope,
            WorkOrder.scheduled_date.is_not(None),
            WorkOrder.scheduled_date < now,
            WorkOrder.status.in_(
                [
                    WorkOrderStatus.OPEN,
                    WorkOrderStatus.ASSIGNED,
                    WorkOrderStatus.IN_PROGRESS,
                    WorkOrderStatus.WAITING,
                ]
            ),
        )
    )
    overdue_preventive_count = db.scalar(
        select(func.count(PreventivePlan.id)).where(
            *preventive_scope,
            PreventivePlan.active.is_(True),
            PreventivePlan.next_execution < now,
        )
    )
    resolved_rows = db.execute(
        select(Incident.reported_at, Incident.resolved_at).where(
            *incident_scope,
            Incident.resolved_at.is_not(None),
            Incident.resolved_at >= period_start,
        )
    ).all()
    resolution_hours = [
        max(0.0, (resolved_at - reported_at).total_seconds() / 3600)
        for reported_at, resolved_at in resolved_rows
        if resolved_at
    ]
    daily_incidents = {
        day.isoformat() if hasattr(day, "isoformat") else str(day): count
        for day, count in db.execute(
            select(func.date(Incident.reported_at), func.count(Incident.id))
            .where(*incident_scope, Incident.reported_at >= period_start)
            .group_by(func.date(Incident.reported_at))
        ).all()
    }
    top_asset_rows = db.execute(
        select(
            Asset.id,
            Asset.code,
            Asset.name,
            func.count(Incident.id),
            func.coalesce(func.sum(Incident.downtime_minutes), 0),
        )
        .join(Incident, Incident.asset_id == Asset.id)
        .where(
            *incident_scope,
            Asset.company_id == company_id,
            Incident.reported_at >= period_start,
        )
        .group_by(Asset.id, Asset.code, Asset.name)
        .order_by(
            func.coalesce(func.sum(Incident.downtime_minutes), 0).desc(),
            func.count(Incident.id).desc(),
        )
        .limit(5)
    ).all()
    active_order_statuses = [
        WorkOrderStatus.OPEN,
        WorkOrderStatus.ASSIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.WAITING,
    ]
    active_session_query = (
        select(
            WorkSession.user_id.label("user_id"),
            func.count(WorkSession.id).label("active_sessions"),
        )
        .join(WorkOrder, WorkOrder.id == WorkSession.work_order_id)
        .where(
            WorkSession.company_id == company_id,
            WorkOrder.company_id == company_id,
            WorkSession.ended_at.is_(None),
        )
    )
    if plant_id:
        active_session_query = active_session_query.where(WorkOrder.plant_id == plant_id)
    active_session_counts = active_session_query.group_by(WorkSession.user_id).subquery()
    workload_scope = [
        WorkOrder.company_id == company_id,
        WorkOrderParticipant.company_id == company_id,
        User.company_id == company_id,
        WorkOrder.status.in_(active_order_statuses),
        WorkOrderParticipant.active.is_(True),
    ]
    if plant_id:
        workload_scope.append(WorkOrder.plant_id == plant_id)
    workload_rows = db.execute(
        select(
            User.id,
            User.full_name,
            func.count(func.distinct(WorkOrder.id)),
            func.count(
                func.distinct(case((WorkOrder.status == WorkOrderStatus.IN_PROGRESS, WorkOrder.id)))
            ),
            func.coalesce(active_session_counts.c.active_sessions, 0),
        )
        .join(WorkOrderParticipant, WorkOrderParticipant.user_id == User.id)
        .join(WorkOrder, WorkOrder.id == WorkOrderParticipant.work_order_id)
        .outerjoin(active_session_counts, active_session_counts.c.user_id == User.id)
        .where(*workload_scope)
        .group_by(User.id, User.full_name, active_session_counts.c.active_sessions)
        .order_by(func.count(func.distinct(WorkOrder.id)).desc(), User.full_name)
        .limit(8)
    ).all()

    open_incidents = sum(
        incident_counts.get(value, 0)
        for value in [
            IncidentStatus.OPEN,
            IncidentStatus.ASSIGNED,
            IncidentStatus.IN_PROGRESS,
            IncidentStatus.WAITING,
        ]
    )
    pending_orders = sum(
        order_counts.get(value, 0) for value in [WorkOrderStatus.OPEN, WorkOrderStatus.ASSIGNED]
    )
    return DashboardRead(
        period_days=period_days,
        generated_at=now,
        readiness=readiness,
        active_assets=asset_counts.get(AssetStatus.ACTIVE, 0),
        stopped_assets=asset_counts.get(AssetStatus.STOPPED, 0),
        maintenance_assets=asset_counts.get(AssetStatus.MAINTENANCE, 0),
        open_incidents=open_incidents,
        critical_incidents=priority_counts.get(Priority.CRITICAL, 0),
        pending_work_orders=pending_orders,
        in_progress_work_orders=order_counts.get(WorkOrderStatus.IN_PROGRESS, 0),
        completed_work_orders=(
            order_counts.get(WorkOrderStatus.COMPLETED, 0)
            + order_counts.get(WorkOrderStatus.CLOSED, 0)
        ),
        upcoming_preventive_count=upcoming_preventive_count or 0,
        low_stock_items=low_stock_items or 0,
        downtime_hours=round(float(downtime_minutes or 0) / 60, 1),
        mttr_hours=(
            round(sum(resolution_hours) / len(resolution_hours), 1)
            if resolution_hours
            else None
        ),
        resolved_incidents=len(resolution_hours),
        overdue_work_orders=overdue_work_orders or 0,
        overdue_preventive_count=overdue_preventive_count or 0,
        asset_statuses=[
            ChartItem(label=key.value, value=value) for key, value in asset_counts.items()
        ],
        work_order_statuses=[
            ChartItem(label=key.value, value=value) for key, value in order_counts.items()
        ],
        incidents_by_priority=[
            ChartItem(label=key.value, value=value) for key, value in priority_counts.items()
        ],
        incident_trend=_incident_trend(daily_incidents, period_start, now, period_days),
        top_assets=[
            AssetImpact(
                asset_id=asset_id,
                asset_code=code,
                asset_name=name,
                incidents=incidents,
                downtime_hours=round(float(minutes or 0) / 60, 1),
            )
            for asset_id, code, name, incidents, minutes in top_asset_rows
        ],
        technician_workload=[
            TechnicianLoad(
                user_id=user_id,
                full_name=full_name,
                active_work_orders=active_orders,
                in_progress_work_orders=in_progress,
                active_sessions=active_sessions,
            )
            for user_id, full_name, active_orders, in_progress, active_sessions in workload_rows
        ],
        recent_incidents=[
            RecentIncident(
                id=incident.id,
                title=incident.title,
                asset_code=asset_code,
                priority=incident.priority,
                status=incident.status,
                reported_at=incident.reported_at,
            )
            for incident, asset_code in recent_rows
        ],
        upcoming_work_orders=[
            UpcomingWorkOrder(
                id=order.id,
                number=order.number,
                title=order.title,
                asset_code=asset_code,
                status=order.status,
                scheduled_date=order.scheduled_date,
            )
            for order, asset_code in upcoming_rows
        ],
    )


def _incident_trend(
    daily_counts: dict[str, int],
    period_start: datetime,
    now: datetime,
    period_days: int,
) -> list[ChartItem]:
    bucket_days = 1 if period_days <= 30 else 7
    trend: list[ChartItem] = []
    cursor = period_start.date()
    final_day = now.date()
    while cursor <= final_day:
        bucket_end = min(cursor + timedelta(days=bucket_days - 1), final_day)
        value = 0
        day = cursor
        while day <= bucket_end:
            value += daily_counts.get(day.isoformat(), 0)
            day += timedelta(days=1)
        trend.append(ChartItem(label=cursor.isoformat(), value=value))
        cursor = bucket_end + timedelta(days=1)
    return trend


def dashboard_csv(data: DashboardRead) -> str:
    output = StringIO()
    csv = writer(output, lineterminator="\n")
    csv.writerow(["ForgeOps - Informe operativo"])
    csv.writerow(["Generado", data.generated_at.isoformat()])
    csv.writerow(["Periodo (dias)", data.period_days])
    csv.writerow([])
    csv.writerow(["Indicador", "Valor"])
    csv.writerows(
        [
            ["Activos parados", data.stopped_assets],
            ["Incidencias abiertas", data.open_incidents],
            ["Incidencias criticas", data.critical_incidents],
            ["Ordenes vencidas", data.overdue_work_orders],
            ["Ordenes en curso", data.in_progress_work_orders],
            ["Horas de parada", data.downtime_hours],
            ["MTTR (horas)", data.mttr_hours if data.mttr_hours is not None else "Sin datos"],
            ["Incidencias resueltas", data.resolved_incidents],
            ["Preventivos vencidos", data.overdue_preventive_count],
            ["Repuestos bajo minimo", data.low_stock_items],
        ]
    )
    csv.writerow([])
    csv.writerow(["Activo", "Nombre", "Incidencias", "Horas de parada"])
    for asset in data.top_assets:
        csv.writerow(
            [
                _csv_cell(asset.asset_code),
                _csv_cell(asset.asset_name),
                asset.incidents,
                asset.downtime_hours,
            ]
        )
    csv.writerow([])
    csv.writerow(["Tecnico", "OT activas", "OT en curso", "Sesiones activas"])
    for technician in data.technician_workload:
        csv.writerow(
            [
                _csv_cell(technician.full_name),
                technician.active_work_orders,
                technician.in_progress_work_orders,
                technician.active_sessions,
            ]
        )
    return "\ufeff" + output.getvalue()


def _csv_cell(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def _pilot_readiness(db: Session, company_id: uuid.UUID) -> PilotReadiness:
    company = db.get(Company, company_id)
    company_complete = bool(
        company
        and company.name
        and company.tax_id
        and company.address
        and company.email
        and company.industry
    )
    counts = {
        "plants": db.scalar(
            select(func.count(Plant.id)).where(
                Plant.company_id == company_id, Plant.active.is_(True)
            )
        )
        or 0,
        "users": db.scalar(
            select(func.count(User.id)).where(
                User.company_id == company_id, User.active.is_(True)
            )
        )
        or 0,
        "assets": db.scalar(select(func.count(Asset.id)).where(Asset.company_id == company_id))
        or 0,
        "preventives": db.scalar(
            select(func.count(PreventivePlan.id)).where(
                PreventivePlan.company_id == company_id,
                PreventivePlan.active.is_(True),
            )
        )
        or 0,
        "documents": db.scalar(
            select(func.count(TechnicalDocument.id)).where(
                TechnicalDocument.company_id == company_id
            )
        )
        or 0,
        "inventory": db.scalar(
            select(func.count(InventoryItem.id)).where(
                InventoryItem.company_id == company_id,
                InventoryItem.active.is_(True),
            )
        )
        or 0,
    }
    items = [
        SetupItem(
            key="company",
            label="Completar datos de empresa",
            complete=company_complete,
            href="/company",
        ),
        SetupItem(
            key="plants",
            label="Crear una planta activa",
            complete=counts["plants"] > 0,
            href="/plants",
        ),
        SetupItem(
            key="users",
            label="Incorporar al equipo",
            complete=counts["users"] >= 2,
            href="/users",
        ),
        SetupItem(
            key="assets",
            label="Registrar activos",
            complete=counts["assets"] > 0,
            href="/assets",
        ),
    ]
    enabled = set(company.enabled_modules if company else [])
    if CompanyModule.PREVENTIVE.value in enabled:
        items.append(
            SetupItem(
                key="preventives",
                label="Planificar preventivos",
                complete=counts["preventives"] > 0,
                href="/preventive-maintenance",
            )
        )
    if CompanyModule.INVENTORY.value in enabled:
        items.append(
            SetupItem(
                key="inventory",
                label="Preparar el inventario",
                complete=counts["inventory"] > 0,
                href="/inventory",
            )
        )
    if CompanyModule.DOCUMENTS.value in enabled:
        items.append(
            SetupItem(
                key="documents",
                label="Cargar documentacion",
                complete=counts["documents"] > 0,
                href="/documents",
            )
        )
    completed = sum(item.complete for item in items)
    return PilotReadiness(
        percent=round(completed / len(items) * 100),
        completed=completed,
        total=len(items),
        items=items,
    )
