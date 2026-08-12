"use client";

import { Activity, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { useOperatorAuth } from "@/components/operator-auth-provider";
import { PageHeader } from "@/components/page-header";
import { formatDate } from "@/lib/format";
import type { OperatorAuditPage } from "@/lib/types";

export default function OperatorAuditPageView() {
  const { request } = useOperatorAuth();
  const [data, setData] = useState<OperatorAuditPage | null>(null);
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "25" });
    if (search.trim()) params.set("search", search.trim());
    if (action) params.set("action", action);
    try { setData(await request<OperatorAuditPage>(`/operator/audit-events?${params}`)); }
    catch { setError("No se pudo cargar la auditoria de plataforma"); }
  }, [action, page, request, search]);

  useEffect(() => { void load(); }, [load]);

  return <><PageHeader title="Auditoria del operador" description="Registro inmutable de accesos y decisiones comerciales realizadas desde el backoffice." />{error && <ErrorBanner message={error} />}<section className="panel mb-4 grid gap-3 p-4 sm:grid-cols-[1fr_220px_auto]"><label className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Buscar evento o ambito" /></label><select className="field" value={action} onChange={(event) => { setAction(event.target.value); setPage(1); }}><option value="">Todas las acciones</option><option value="LOGIN">Accesos</option><option value="LOGIN_FAILED">Accesos fallidos</option><option value="COMPANY_UPDATE">Cambios de empresa</option><option value="TRIAL_EXTEND">Ampliaciones</option><option value="PASSWORD_CHANGE">Contrasenas</option></select><button className="button-secondary justify-center" onClick={() => void load()}>Actualizar</button></section>{!data && !error ? <LoadingBlock /> : data?.items.length === 0 ? <section className="panel"><EmptyState title="Sin actividad" detail="Los eventos del operador apareceran aqui." /></section> : data && <section className="panel overflow-hidden"><div className="table-wrap"><table className="data-table min-w-[920px]"><thead><tr><th>Evento</th><th>Accion</th><th>Operador</th><th>Fecha</th><th>IP</th></tr></thead><tbody>{data.items.map((event) => <tr key={event.id}><td><p className="font-bold text-[var(--ink)]">{event.summary}</p><p className="mt-1 text-[10px] uppercase text-[var(--muted)]">{event.target_type}</p></td><td><span className="status-badge badge-info">{operatorAction(event.action)}</span></td><td>{event.operator?.full_name ?? "Sistema"}</td><td>{formatDate(event.created_at, true)}</td><td>{event.ip_address ?? "Interna"}</td></tr>)}</tbody></table></div><footer className="flex items-center justify-between border-t border-[var(--line)] px-4 py-3"><p className="text-xs text-[var(--muted)]">{data.total} eventos · pagina {data.page} de {data.pages}</p><div className="flex gap-2"><button className="icon-button" disabled={data.page <= 1} onClick={() => setPage((value) => value - 1)} aria-label="Pagina anterior"><ChevronLeft size={17} /></button><button className="icon-button" disabled={data.page >= data.pages} onClick={() => setPage((value) => value + 1)} aria-label="Pagina siguiente"><ChevronRight size={17} /></button></div></footer></section>}<div className="mt-4 flex items-start gap-3 rounded-md border border-[var(--line)] bg-white p-4"><Activity className="mt-0.5 shrink-0 text-[var(--accent)]" size={17} /><p className="text-xs leading-5 text-[var(--muted)]">Los eventos conservan operador, fecha, IP, valores anteriores, valores nuevos y motivo cuando corresponde.</p></div></>;
}

function operatorAction(value: string): string {
  const labels: Record<string, string> = { LOGIN: "Acceso", LOGIN_FAILED: "Acceso fallido", COMPANY_UPDATE: "Cambio comercial", TRIAL_EXTEND: "Ampliacion", PASSWORD_CHANGE: "Contrasena", BOOTSTRAP: "Alta inicial" };
  return labels[value] ?? value;
}
