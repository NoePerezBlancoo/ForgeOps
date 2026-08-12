const labels: Record<string, string> = {
  ACTIVE: "Activo",
  STOPPED: "Parado",
  MAINTENANCE: "En mantenimiento",
  OUT_OF_SERVICE: "Fuera de servicio",
  LOW: "Baja",
  MEDIUM: "Media",
  HIGH: "Alta",
  CRITICAL: "Critica",
  OPEN: "Abierta",
  ASSIGNED: "Asignada",
  IN_PROGRESS: "En curso",
  WAITING: "En espera",
  RESOLVED: "Resuelta",
  CLOSED: "Cerrada",
  COMPLETED: "Completada",
  CANCELLED: "Cancelada",
  CORRECTIVE: "Correctivo",
  PREVENTIVE: "Preventivo",
  INSPECTION: "Inspeccion",
  IMPROVEMENT: "Mejora",
  SUPER_ADMIN: "Superadministrador",
  ADMIN: "Administrador",
  MAINTENANCE_MANAGER: "Responsable de mantenimiento",
  TECHNICIAN: "Tecnico",
  VIEWER: "Consulta",
};

export function labelFor(value: string): string {
  return labels[value] ?? value;
}

export function formatDate(value: string | null, includeTime = false): string {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-ES", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(includeTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(new Date(value));
}

export function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

