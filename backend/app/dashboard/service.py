import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assets.models import Asset
from app.core.enums import AssetStatus, IncidentStatus, Priority, WorkOrderStatus
from app.dashboard.schemas import ChartItem, DashboardRead, RecentIncident, UpcomingWorkOrder
from app.incidents.models import Incident
from app.work_orders.models import WorkOrder


def dashboard_data(db: Session, company_id: uuid.UUID) -> DashboardRead:
    asset_counts = dict(
        db.execute(
            select(Asset.status, func.count(Asset.id))
            .where(Asset.company_id == company_id)
            .group_by(Asset.status)
        ).all()
    )
    incident_counts = dict(
        db.execute(
            select(Incident.status, func.count(Incident.id))
            .where(Incident.company_id == company_id)
            .group_by(Incident.status)
        ).all()
    )
    priority_counts = dict(
        db.execute(
            select(Incident.priority, func.count(Incident.id))
            .where(
                Incident.company_id == company_id,
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]),
            )
            .group_by(Incident.priority)
        ).all()
    )
    order_counts = dict(
        db.execute(
            select(WorkOrder.status, func.count(WorkOrder.id))
            .where(WorkOrder.company_id == company_id)
            .group_by(WorkOrder.status)
        ).all()
    )
    downtime_minutes = db.scalar(
        select(func.coalesce(func.sum(Incident.downtime_minutes), 0)).where(
            Incident.company_id == company_id,
            Incident.reported_at >= datetime.now(UTC) - timedelta(days=30),
        )
    )
    recent_rows = db.execute(
        select(Incident, Asset.code)
        .join(Asset, Asset.id == Incident.asset_id)
        .where(Incident.company_id == company_id)
        .order_by(Incident.reported_at.desc())
        .limit(5)
    ).all()
    upcoming_rows = db.execute(
        select(WorkOrder, Asset.code)
        .join(Asset, Asset.id == WorkOrder.asset_id)
        .where(
            WorkOrder.company_id == company_id,
            WorkOrder.status.notin_([WorkOrderStatus.COMPLETED, WorkOrderStatus.CANCELLED]),
        )
        .order_by(WorkOrder.scheduled_date.asc().nullslast(), WorkOrder.created_at.desc())
        .limit(5)
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
        active_assets=asset_counts.get(AssetStatus.ACTIVE, 0),
        stopped_assets=asset_counts.get(AssetStatus.STOPPED, 0),
        maintenance_assets=asset_counts.get(AssetStatus.MAINTENANCE, 0),
        open_incidents=open_incidents,
        critical_incidents=priority_counts.get(Priority.CRITICAL, 0),
        pending_work_orders=pending_orders,
        in_progress_work_orders=order_counts.get(WorkOrderStatus.IN_PROGRESS, 0),
        completed_work_orders=order_counts.get(WorkOrderStatus.COMPLETED, 0),
        downtime_hours=round(float(downtime_minutes or 0) / 60, 1),
        asset_statuses=[
            ChartItem(label=key.value, value=value) for key, value in asset_counts.items()
        ],
        work_order_statuses=[
            ChartItem(label=key.value, value=value) for key, value in order_counts.items()
        ],
        incidents_by_priority=[
            ChartItem(label=key.value, value=value) for key, value in priority_counts.items()
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
