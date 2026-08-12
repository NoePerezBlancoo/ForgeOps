export type UserRole =
  | "SUPER_ADMIN"
  | "ADMIN"
  | "MAINTENANCE_MANAGER"
  | "TECHNICIAN"
  | "VIEWER";

export type CompanyPlan =
  | "DEMO"
  | "TRIAL"
  | "STARTER"
  | "PRO"
  | "INDUSTRIAL"
  | "ENTERPRISE"
  | "PROFESSIONAL";
export type SubscriptionStatus = "TRIAL" | "ACTIVE" | "SUSPENDED";
export type AccessStatus = SubscriptionStatus | "EXPIRED";
export type CompanyModule = "PREVENTIVE" | "INVENTORY" | "DOCUMENTS" | "KNOWLEDGE";

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
  plan: CompanyPlan;
  subscription_status: SubscriptionStatus;
  access_status: AccessStatus;
  trial_ends_at: string | null;
  trial_days_remaining: number | null;
  write_enabled: boolean;
  enabled_modules: CompanyModule[];
}

export interface Company extends CompanySummary {
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  industry: string | null;
  timezone: string;
  locale: string;
  work_order_prefix: string;
  trial_started_at: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  company_id: string;
  full_name: string;
  email: string;
  job_title: string | null;
  phone: string | null;
  role: UserRole;
  active: boolean;
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
  updated_at: string;
  company: CompanySummary;
}

export interface UserOption {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  active: boolean;
}

export interface PlatformOperator {
  id: string;
  full_name: string;
  email: string;
  active: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  password_changed_at: string | null;
  created_at: string;
}

export interface OperatorCompanySummary {
  id: string;
  name: string;
  email: string | null;
  industry: string | null;
  plan: CompanyPlan;
  subscription_status: SubscriptionStatus;
  access_status: AccessStatus;
  trial_started_at: string | null;
  trial_ends_at: string | null;
  trial_days_remaining: number | null;
  enabled_modules: CompanyModule[];
  active: boolean;
  created_at: string;
  users_count: number;
  plants_count: number;
  assets_count: number;
  open_incidents_count: number;
  open_work_orders_count: number;
  last_activity_at: string | null;
}

export interface OperatorCompanyDetail extends OperatorCompanySummary {
  tax_id: string | null;
  address: string | null;
  phone: string | null;
  timezone: string;
  locale: string;
  work_order_prefix: string;
  updated_at: string;
  administrators: Array<{
    id: string;
    full_name: string;
    email: string;
    active: boolean;
    last_login_at: string | null;
  }>;
  limits: Record<string, number | null>;
  usage: Record<string, number>;
  limit_overrides: Record<string, number | null>;
  feature_overrides: Record<string, boolean>;
}

export interface OperatorCompanyPage {
  items: OperatorCompanySummary[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface OperatorDashboard {
  total_companies: number;
  active_trials: number;
  expiring_trials: number;
  expired_trials: number;
  active_customers: number;
  suspended_companies: number;
  active_users: number;
  total_assets: number;
  open_incidents: number;
  open_work_orders: number;
  module_adoption: Record<CompanyModule, number>;
  recent_companies: OperatorCompanySummary[];
}

export interface OperatorAuditEvent {
  id: string;
  action: string;
  target_type: string;
  target_id: string | null;
  summary: string;
  context: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
  operator: Pick<PlatformOperator, "id" | "full_name" | "email"> | null;
}

export interface OperatorAuditPage {
  items: OperatorAuditEvent[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Plant {
  id: string;
  company_id: string;
  name: string;
  code: string;
  address: string | null;
  description: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  summary: string;
  context: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
  actor: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface AuditSummary {
  total_events: number;
  active_sessions: number;
  administrators: number;
  last_event_at: string | null;
}

export interface AuthSession {
  id: string;
  created_at: string;
  expires_at: string;
  current: boolean;
}

export interface TrialRegistration {
  company_name: string;
  industry: string;
  plant_name: string;
  full_name: string;
  email: string;
  password: string;
  sample_data: boolean;
  terms_accepted: boolean;
}

export interface OnboardingStep {
  key: string;
  title: string;
  description: string;
  href: string;
  complete: boolean;
  automatic: boolean;
}

export interface Onboarding {
  completed: number;
  total: number;
  percent: number;
  tour_completed: boolean;
  dismissed_at: string | null;
  steps: OnboardingStep[];
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
  readiness: {
    percent: number;
    completed: number;
    total: number;
    items: Array<{ key: string; label: string; complete: boolean; href: string }>;
  };
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
