from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.enums import IncidentStatus, Priority, WorkOrderStatus


class MetricCard(BaseModel):
    value: float
    change: float | None = None


class ChartItem(BaseModel):
    label: str
    value: float


class RecentIncident(BaseModel):
    id: UUID
    title: str
    asset_code: str
    priority: Priority
    status: IncidentStatus
    reported_at: datetime


class UpcomingWorkOrder(BaseModel):
    id: UUID
    number: str
    title: str
    asset_code: str
    status: WorkOrderStatus
    scheduled_date: datetime | None


class DashboardRead(BaseModel):
    active_assets: int
    stopped_assets: int
    maintenance_assets: int
    open_incidents: int
    critical_incidents: int
    pending_work_orders: int
    in_progress_work_orders: int
    completed_work_orders: int
    downtime_hours: float
    asset_statuses: list[ChartItem]
    work_order_statuses: list[ChartItem]
    incidents_by_priority: list[ChartItem]
    recent_incidents: list[RecentIncident]
    upcoming_work_orders: list[UpcomingWorkOrder]
