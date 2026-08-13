"use client";

import { AlertTriangle, CheckCircle2, CloudOff, RefreshCw, Trash2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/format";
import {
  listOfflineOperations,
  removeOfflineOperation,
  retryOfflineOperation,
  type OfflineOperation,
  type OfflineOwner,
} from "@/lib/offline-queue";
import { useOnlineStatus } from "@/lib/use-online-status";

export default function SyncPage() {
  const { user } = useAuth();
  const online = useOnlineStatus();
  const [operations, setOperations] = useState<OfflineOperation[]>([]);
  const [error, setError] = useState("");
  const owner = useMemo<OfflineOwner | null>(
    () => user ? { companyId: user.company_id, userId: user.id } : null,
    [user],
  );

  const reload = useCallback(async () => {
    if (!owner || !("indexedDB" in window)) return;
    try {
      setOperations(await listOfflineOperations(owner));
      setError("");
    } catch {
      setError("No se pudo leer la cola local de este dispositivo.");
    }
  }, [owner]);

  useEffect(() => {
    const handleChange = () => void reload();
    window.addEventListener("forgeops:queue-change", handleChange);
    void reload();
    return () => window.removeEventListener("forgeops:queue-change", handleChange);
  }, [reload]);

  function synchronize() {
    window.dispatchEvent(new Event("forgeops:sync-request"));
  }

  async function retry(operation: OfflineOperation) {
    await retryOfflineOperation(operation);
    if (online) synchronize();
  }

  async function discard(operation: OfflineOperation) {
    if (!window.confirm("Descartar definitivamente este cambio local?")) return;
    await removeOfflineOperation(operation.id);
  }

  const conflicts = operations.filter((operation) => operation.status === "CONFLICT").length;
  const failed = operations.filter((operation) => operation.status === "FAILED").length;

  return (
    <>
      <PageHeader
        title="Sincronizacion"
        description="Cambios guardados en este dispositivo pendientes de consolidar en ForgeOps."
        actions={operations.length > 0 ? (
          <button className="button-primary" onClick={synchronize} disabled={!online}>
            <RefreshCw size={16} /> Sincronizar
          </button>
        ) : undefined}
      />
      {error && <ErrorBanner message={error} />}
      {!online && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">
          <CloudOff size={17} /> Los cambios se enviaran cuando vuelva la conexion.
        </div>
      )}
      {conflicts > 0 && (
        <div className="mb-4 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-800">
          <AlertTriangle size={17} /> {conflicts} {conflicts === 1 ? "cambio requiere" : "cambios requieren"} revision manual.
        </div>
      )}

      <section className="panel overflow-hidden">
        {operations.length === 0 ? (
          <EmptyState title="Todo sincronizado" detail="No hay cambios locales pendientes en este dispositivo." />
        ) : (
          <div className="divide-y divide-[var(--line)]">
            {operations.map((operation) => (
              <article key={operation.id} className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
                <span className={`grid size-10 shrink-0 place-items-center rounded-md ${operation.status === "CONFLICT" ? "bg-red-50 text-red-700" : operation.status === "FAILED" ? "bg-amber-50 text-amber-800" : "bg-emerald-50 text-emerald-700"}`}>
                  {operation.status === "CONFLICT" || operation.status === "FAILED" ? <AlertTriangle size={19} /> : <RefreshCw size={18} />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-bold text-[var(--ink)]">{operationLabel(operation)}</p>
                    <StatusBadge value={operation.status} />
                  </div>
                  <p className="mt-1 truncate text-xs text-[var(--muted)]">{operationSummary(operation)}</p>
                  <p className="mt-1 text-[10px] font-semibold text-[var(--muted)]">
                    Creado {formatDate(operation.createdAt, true)} · {operation.attempts} intentos
                  </p>
                  {operation.error && <p className="mt-2 text-xs font-semibold text-red-700">{operation.error}</p>}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {["FAILED", "CONFLICT"].includes(operation.status) && (
                    <button className="button-secondary" onClick={() => void retry(operation)}>
                      <RefreshCw size={15} /> Reintentar
                    </button>
                  )}
                  <button className="icon-button" onClick={() => void discard(operation)} aria-label="Descartar cambio" title="Descartar">
                    <Trash2 size={16} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <div className="mt-4 flex items-start gap-3 rounded-md border border-[var(--line)] bg-white px-4 py-3 text-xs leading-5 text-[var(--muted)]">
        <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={16} />
        La cola esta aislada por empresa y usuario. Al cerrar sesion se eliminan todos los datos locales de la cuenta.
        {failed > 0 ? ` Hay ${failed} cambios fallidos que puedes reintentar.` : ""}
      </div>
    </>
  );
}

function operationLabel(operation: OfflineOperation): string {
  return operation.type === "INCIDENT_CREATE" ? "Nueva incidencia" : "Nota de intervencion";
}

function operationSummary(operation: OfflineOperation): string {
  const value = operation.type === "INCIDENT_CREATE" ? operation.payload.title : operation.payload.body;
  return typeof value === "string" ? value : operation.path;
}
