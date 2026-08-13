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


class AssetImpact(BaseModel):
    asset_id: UUID
    asset_code: str
    asset_name: str
    incidents: int
    downtime_hours: float


class TechnicianLoad(BaseModel):
    user_id: UUID
    full_name: str
    active_work_orders: int
    in_progress_work_orders: int
    active_sessions: int


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


class SetupItem(BaseModel):
    key: str
    label: str
    complete: bool
    href: str


class PilotReadiness(BaseModel):
    percent: int
    completed: int
    total: int
    items: list[SetupItem]


class DashboardRead(BaseModel):
    period_days: int
    generated_at: datetime
    readiness: PilotReadiness
    active_assets: int
    stopped_assets: int
    maintenance_assets: int
    open_incidents: int
    critical_incidents: int
    pending_work_orders: int
    in_progress_work_orders: int
    completed_work_orders: int
    upcoming_preventive_count: int
    low_stock_items: int
    downtime_hours: float
    mttr_hours: float | None
    resolved_incidents: int
    overdue_work_orders: int
    overdue_preventive_count: int
    asset_statuses: list[ChartItem]
    work_order_statuses: list[ChartItem]
    incidents_by_priority: list[ChartItem]
    incident_trend: list[ChartItem]
    top_assets: list[AssetImpact]
    technician_workload: list[TechnicianLoad]
    recent_incidents: list[RecentIncident]
    upcoming_work_orders: list[UpcomingWorkOrder]
