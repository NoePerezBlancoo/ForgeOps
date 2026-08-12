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
export type FrequencyType = "DAYS" | "WEEKS" | "MONTHS" | "YEARS";
export type InventoryMovementType = "RECEIPT" | "CONSUMPTION" | "ADJUSTMENT";
export type DocumentType = "MANUAL" | "ELECTRICAL_SCHEMATIC" | "PROCEDURE" | "SAFETY" | "OTHER";
export type DocumentIndexStatus = "PENDING" | "INDEXING" | "READY" | "FAILED" | "UNSUPPORTED";

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
  preventive_plan_id: string | null;
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
  upcoming_preventive_count: number;
  low_stock_items: number;
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

export interface PreventivePlan {
  id: string;
  company_id: string;
  asset_id: string;
  assigned_to: string | null;
  name: string;
  description: string;
  frequency_type: FrequencyType;
  frequency_value: number;
  next_execution: string;
  estimated_duration: number;
  priority: Priority;
  active: boolean;
  last_generated_at: string | null;
  created_at: string;
  updated_at: string;
  asset: Pick<Asset, "id" | "code" | "name">;
  assignee: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface InventoryItem {
  id: string;
  company_id: string;
  code: string;
  name: string;
  description: string | null;
  stock: string;
  minimum_stock: string;
  unit: string;
  location: string | null;
  cost: string | null;
  active: boolean;
  low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: string;
  item_id: string;
  user_id: string;
  movement_type: InventoryMovementType;
  quantity: string;
  resulting_stock: string;
  reason: string;
  created_at: string;
  user: Pick<User, "id" | "full_name" | "email">;
}

export interface TechnicalDocument {
  id: string;
  company_id: string;
  asset_id: string;
  uploaded_by: string;
  name: string;
  type: DocumentType;
  original_name: string;
  mime_type: string;
  file_size: number;
  description: string | null;
  uploaded_at: string;
  index_status: DocumentIndexStatus;
  indexed_at: string | null;
  index_error: string | null;
  chunk_count: number;
  embedded_chunk_count: number;
  embedding_model: string | null;
  asset: Pick<Asset, "id" | "code" | "name">;
  uploader: Pick<User, "id" | "full_name" | "email">;
}

export interface KnowledgeStatus {
  configured_provider: string;
  effective_provider: "local" | "openai";
  generation_available: boolean;
  semantic_search_available: boolean;
  chat_model: string | null;
  embedding_model: string | null;
  indexed_documents: number;
  pending_documents: number;
  failed_documents: number;
  unsupported_documents: number;
  chunks: number;
  embedded_chunks: number;
  configuration_warning: string | null;
}

export interface KnowledgeSource {
  chunk_id: string;
  document_id: string;
  document_name: string;
  original_name: string;
  asset_id: string;
  asset_code: string;
  asset_name: string;
  page_number: number | null;
  excerpt: string;
  score: number;
}

export interface KnowledgeAnswer {
  query_id: string;
  answer: string;
  mode: "extractive" | "generative" | "insufficient";
  provider: string;
  model: string | null;
  confidence: number;
  duration_ms: number;
  sources: KnowledgeSource[];
}

export interface KnowledgeHistory {
  id: string;
  question: string;
  answer: string;
  mode: string;
  provider: string;
  model: string | null;
  confidence: number;
  source_count: number;
  duration_ms: number;
  created_at: string;
}
