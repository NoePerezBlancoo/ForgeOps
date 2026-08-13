import { labelFor } from "@/lib/format";

const tones: Record<string, string> = {
  ACTIVE: "badge-success",
  COMPLETED: "badge-success",
  RESOLVED: "badge-success",
  CLOSED: "badge-neutral",
  OPEN: "badge-info",
  ASSIGNED: "badge-info",
  IN_PROGRESS: "badge-warning",
  WAITING: "badge-neutral",
  PENDING_VALIDATION: "badge-warning",
  STOPPED: "badge-danger",
  OUT_OF_SERVICE: "badge-neutral",
  MAINTENANCE: "badge-warning",
  CRITICAL: "badge-danger",
  HIGH: "badge-orange",
  MEDIUM: "badge-info",
  LOW: "badge-neutral",
  CANCELLED: "badge-neutral",
  PENDING: "badge-warning",
  INDEXING: "badge-info",
  READY: "badge-success",
  FAILED: "badge-danger",
  UNSUPPORTED: "badge-neutral",
  TRIAL: "badge-info",
  SUSPENDED: "badge-danger",
  EXPIRED: "badge-danger",
  INACTIVE: "badge-neutral",
  ACCEPTED: "badge-success",
  REVOKED: "badge-neutral",
  PROFESSIONAL: "badge-success",
  STARTER: "badge-info",
  PRO: "badge-success",
  INDUSTRIAL: "badge-warning",
  ENTERPRISE: "badge-neutral",
  DEMO: "badge-warning",
};

export function StatusBadge({ value }: { value: string }) {
  return <span className={`status-badge ${tones[value] ?? "badge-neutral"}`}>{labelFor(value)}</span>;
}
