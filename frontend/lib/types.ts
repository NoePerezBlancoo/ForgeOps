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
  | "PENDING_VALIDATION"
  | "COMPLETED"
  | "CLOSED"
  | "CANCELLED";
export type WorkOrderType = "CORRECTIVE" | "PREVENTIVE" | "INSPECTION" | "IMPROVEMENT";
export type WorkOrderParticipantRole = "LEAD" | "TECHNICIAN" | "SUPPORT";
export type WorkSessionEndReason = "PAUSED" | "COMPLETED" | "CANCELLED" | "REMOVED";
export type WorkOrderNoteType = "COMMENT" | "MEASUREMENT" | "WORK_LOG" | "CAUSE" | "SOLUTION";
export type WorkOrderEventType =
  | "CREATED"
  | "UPDATED"
  | "ASSIGNED"
  | "PARTICIPANT_ADDED"
  | "PARTICIPANT_REMOVED"
  | "STARTED"
  | "PAUSED"
  | "RESUMED"
  | "NOTE_ADDED"
  | "CHECKLIST_UPDATED"
  | "MATERIAL_CONSUMED"
  | "MATERIAL_RETURNED"
  | "STATUS_CHANGED"
  | "COMPLETED"
  | "VALIDATED"
  | "CLOSED"
  | "REOPENED";
export type FrequencyType = "DAYS" | "WEEKS" | "MONTHS" | "YEARS";
export type InventoryMovementType = "RECEIPT" | "CONSUMPTION" | "ADJUSTMENT" | "RETURN";
export type DocumentType = "MANUAL" | "ELECTRICAL_SCHEMATIC" | "PROCEDURE" | "SAFETY" | "OTHER";
export type DocumentIndexStatus = "PENDING" | "INDEXING" | "READY" | "FAILED" | "UNSUPPORTED";

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  sort: string;
  filters: Record<string, string | boolean>;
}

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

export type InvitationStatus = "PENDING" | "ACCEPTED" | "EXPIRED" | "REVOKED";

export interface UserInvitation {
  id: string;
  company_id: string;
  email: string;
  full_name: string;
  job_title: string | null;
  phone: string | null;
  role: UserRole;
  inviter_id: string | null;
  accepted_user_id: string | null;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
  updated_at: string;
  status: InvitationStatus;
}

export interface UserInvitationList {
  items: UserInvitation[];
  pending: number;
}

export type NotificationType =
  | "WORK_ORDER_ASSIGNED"
  | "CRITICAL_INCIDENT"
  | "PREVENTIVE_DUE"
  | "PREVENTIVE_OVERDUE"
  | "LOW_STOCK"
  | "TRIAL_EXPIRING";

export interface AppNotification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  href: string | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationList {
  items: AppNotification[];
  total: number;
  unread: number;
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
  total_plants: number;
  total_assets: number;
  open_incidents: number;
  open_work_orders: number;
  storage_bytes: number;
  queue_depth: number | null;
  failed_jobs: number;
  service_status: Record<string, string>;
  version: string;
  environment: string;
  commit: string;
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
  validated_by: string | null;
  closed_by: string | null;
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
  work_performed: string | null;
  failure_cause: string | null;
  root_cause: string | null;
  resolution: string | null;
  validated_at: string | null;
  closed_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  asset: Pick<Asset, "id" | "code" | "name">;
  assignee: Pick<User, "id" | "full_name" | "email"> | null;
  creator: Pick<User, "id" | "full_name" | "email">;
}

export interface WorkOrderParticipant {
  id: string;
  user_id: string;
  assigned_by: string | null;
  role: WorkOrderParticipantRole;
  active: boolean;
  joined_at: string;
  removed_at: string | null;
  user: Pick<User, "id" | "full_name" | "email">;
  assigner: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface WorkSession {
  id: string;
  user_id: string;
  started_at: string;
  ended_at: string | null;
  ended_reason: WorkSessionEndReason | null;
  duration_seconds: number | null;
  user: Pick<User, "id" | "full_name" | "email">;
}

export interface WorkOrderNote {
  id: string;
  author_id: string | null;
  note_type: WorkOrderNoteType;
  body: string;
  created_at: string;
  author: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface WorkOrderEvent {
  id: string;
  actor_id: string | null;
  sequence_no: number;
  event_type: WorkOrderEventType;
  summary: string;
  details: Record<string, unknown>;
  occurred_at: string;
  actor: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface WorkOrderChecklistItem {
  id: string;
  company_id: string;
  work_order_id: string;
  source_template_item_id: string | null;
  title: string;
  instructions: string | null;
  position: number;
  required: boolean;
  completed_by: string | null;
  completed_at: string | null;
  notes: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  completer: Pick<User, "id" | "full_name" | "email"> | null;
}

export interface WorkOrderDetail extends WorkOrder {
  validator: Pick<User, "id" | "full_name" | "email"> | null;
  closer: Pick<User, "id" | "full_name" | "email"> | null;
  participants: WorkOrderParticipant[];
  sessions: WorkSession[];
  notes: WorkOrderNote[];
  events: WorkOrderEvent[];
  checklist_items: WorkOrderChecklistItem[];
  inventory_movements: InventoryMovement[];
  material_cost: string;
}

export interface DashboardData {
  period_days: number;
  generated_at: string;
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
  mttr_hours: number | null;
  resolved_incidents: number;
  overdue_work_orders: number;
  overdue_preventive_count: number;
  asset_statuses: Array<{ label: string; value: number }>;
  work_order_statuses: Array<{ label: string; value: number }>;
  incidents_by_priority: Array<{ label: string; value: number }>;
  incident_trend: Array<{ label: string; value: number }>;
  top_assets: Array<{
    asset_id: string;
    asset_code: string;
    asset_name: string;
    incidents: number;
    downtime_hours: number;
  }>;
  technician_workload: Array<{
    user_id: string;
    full_name: string;
    active_work_orders: number;
    in_progress_work_orders: number;
    active_sessions: number;
  }>;
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
  checklist_template_id: string | null;
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
  checklist_template: ChecklistTemplate | null;
}

export interface ChecklistTemplateItem {
  id: string;
  company_id: string;
  template_id: string;
  title: string;
  instructions: string | null;
  position: number;
  required: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChecklistTemplate {
  id: string;
  company_id: string;
  name: string;
  description: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
  items: ChecklistTemplateItem[];
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
  version: number;
  low_stock: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryMovement {
  id: string;
  company_id: string;
  item_id: string;
  user_id: string;
  work_order_id: string | null;
  reversal_of_id: string | null;
  movement_type: InventoryMovementType;
  quantity: string;
  resulting_stock: string;
  unit_cost: string;
  total_cost: string;
  reason: string;
  created_at: string;
  user: Pick<User, "id" | "full_name" | "email">;
  item: Pick<InventoryItem, "id" | "code" | "name" | "unit">;
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
