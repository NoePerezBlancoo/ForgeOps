export type UserRole =
  | "SUPER_ADMIN"
  | "ADMIN"
  | "MAINTENANCE_MANAGER"
  | "TECHNICIAN"
  | "VIEWER";

export type AssetStatus = "ACTIVE" | "STOPPED" | "MAINTENANCE" | "OUT_OF_SERVICE";
export type Criticality = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Priority = Criticality;
export type IncidentStatus =
  | "OPEN"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "WAITING"
  | "RESOLVED"
  | "CLOSED";
export type WorkOrderStatus =
  | "OPEN"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "WAITING"
  | "COMPLETED"
  | "CANCELLED";
export type WorkOrderType = "CORRECTIVE" | "PREVENTIVE" | "INSPECTION" | "IMPROVEMENT";

export interface CompanySummary {
  id: string;
  name: string;
}

export interface User {
  id: string;
  company_id: string;
  full_name: string;
  email: string;
  role: UserRole;
  active: boolean;
  created_at: string;
  company: CompanySummary;
}

export interface UserOption {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
}

export interface Plant {
  id: string;
  company_id: string;
  name: string;
  code: string;
  address: string | null;
  description: string | null;
  active: boolean;
}

export interface Asset {
  id: string;
  company_id: string;
  plant_id: string;
  code: string;
  name: string;
  description: string | null;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  installation_date: string | null;
  status: AssetStatus;
  criticality: Criticality;
  location: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  plant: Pick<Plant, "id" | "name" | "code">;
}

export interface Incident {
  id: string;
  company_id: string;
  plant_id: string;
  asset_id: string;
  reported_by: string;
  assigned_to: string | null;
  title: string;
  description: string;
  priority: Priority;
  status: IncidentStatus;
  reported_at: string;
  started_at: string | null;
  resolved_at: string | null;
  downtime_minutes: number;
  root_cause: string | null;
  resolution: string | null;
  asset: Pick<Asset, "id" | "code" | "name">;
  reporter: Pick<User, "id" | "full_name" | "email">;
  assignee: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface WorkOrder {
  id: string;
  company_id: string;
  plant_id: string;
  asset_id: string;
  incident_id: string | null;
  assigned_to: string | null;
  created_by: string;
  number: string;
  title: string;
  description: string;
  type: WorkOrderType;
  priority: Priority;
  status: WorkOrderStatus;
  scheduled_date: string | null;
  started_at: string | null;
  completed_at: string | null;
  estimated_duration: number | null;
  real_duration: number | null;
  observations: string | null;
  created_at: string;
  asset: Pick<Asset, "id" | "code" | "name">;
  assignee: Pick<User, "id" | "full_name" | "email"> | null;
  creator: Pick<User, "id" | "full_name" | "email">;
}

export interface DashboardData {
  active_assets: number;
  stopped_assets: number;
  maintenance_assets: number;
  open_incidents: number;
  critical_incidents: number;
  pending_work_orders: number;
  in_progress_work_orders: number;
  completed_work_orders: number;
  downtime_hours: number;
  asset_statuses: Array<{ label: string; value: number }>;
  work_order_statuses: Array<{ label: string; value: number }>;
  incidents_by_priority: Array<{ label: string; value: number }>;
  recent_incidents: Array<{
    id: string;
    title: string;
    asset_code: string;
    priority: Priority;
    status: IncidentStatus;
    reported_at: string;
  }>;
  upcoming_work_orders: Array<{
    id: string;
    number: string;
    title: string;
    asset_code: string;
    status: WorkOrderStatus;
    scheduled_date: string | null;
  }>;
}

