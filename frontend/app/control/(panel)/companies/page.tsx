"use client";

import { Building2, ChevronLeft, ChevronRight, Search, Settings2, TimerReset } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { useOperatorAuth } from "@/components/operator-auth-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { CompanyModule, CompanyPlan, OperatorCompanyDetail, OperatorCompanyPage, OperatorCompanySummary, SubscriptionStatus } from "@/lib/types";

const modules: Array<{ key: CompanyModule; label: string }> = [
  { key: "PREVENTIVE", label: "Preventivos" },
  { key: "INVENTORY", label: "Inventario" },
  { key: "DOCUMENTS", label: "Documentos" },
  { key: "KNOWLEDGE", label: "IA documental" },
];

const limitFields = [
  { key: "users", label: "Usuarios" },
  { key: "plants", label: "Plantas" },
  { key: "assets", label: "Activos" },
  { key: "storage_bytes", label: "Almacenamiento (GB)" },
];

export default function OperatorCompaniesPage() {
  const { request } = useOperatorAuth();
  const [pageData, setPageData] = useState<OperatorCompanyPage | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<OperatorCompanyDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: "20", sort: "created" });
    if (search.trim()) params.set("search", search.trim());
    if (status) params.set("access_status", status);
    try {
      setPageData(await request<OperatorCompanyPage>(`/operator/companies?${params}`));
    } catch {
      setError("No se pudo cargar la cartera de empresas");
    }
  }, [page, request, search, status]);

  useEffect(() => { void load(); }, [load]);

  async function openCompany(company: OperatorCompanySummary) {
    setLoadingDetail(true);
    setError("");
    try {
      setSelected(await request<OperatorCompanyDetail>(`/operator/companies/${company.id}`));
    } catch {
      setError("No se pudo abrir la empresa");
    } finally {
      setLoadingDetail(false);
    }
  }

  async function updateCompany(payload: Record<string, unknown>) {
    if (!selected) return;
    const updated = await request<OperatorCompanyDetail>(`/operator/companies/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    setSelected(updated);
    setNotice("Configuracion de empresa actualizada");
    await load();
  }

  async function extendTrial(days: number, reason: string) {
    if (!selected) return;
    const updated = await request<OperatorCompanyDetail>(`/operator/companies/${selected.id}/extend-trial`, { method: "POST", body: JSON.stringify({ days, reason }) });
    setSelected(updated);
    setNotice(`Prueba ampliada ${days} dias`);
    await load();
  }

  return (
    <>
      <PageHeader title="Empresas y suscripciones" description="Gestiona altas, pruebas, planes y capacidades sin acceder a los datos tecnicos del cliente." />
      {notice && <div className="notice-success">{notice}</div>}
      {error && <ErrorBanner message={error} />}
      <section className="panel mb-4 grid gap-3 p-4 sm:grid-cols-[1fr_210px_auto]">
        <label className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Buscar empresa, correo o sector" /></label>
        <select className="field" value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="TRIAL">Pruebas activas</option><option value="ACTIVE">Clientes activos</option><option value="EXPIRED">Pruebas caducadas</option><option value="SUSPENDED">Suspendidas</option><option value="INACTIVE">Inactivas</option></select>
        <button className="button-secondary justify-center" onClick={() => void load()}>Actualizar</button>
      </section>

      {!pageData && !error ? <LoadingBlock /> : pageData?.items.length === 0 ? <section className="panel"><EmptyState title="Sin resultados" detail="No hay empresas que coincidan con los filtros." /></section> : pageData && (
        <section className="panel overflow-hidden">
          <div className="table-wrap"><table className="data-table min-w-[1080px]"><thead><tr><th>Empresa</th><th>Acceso</th><th>Plan</th><th>Uso</th><th>Actividad</th><th className="w-16">Accion</th></tr></thead><tbody>{pageData.items.map((company) => <tr key={company.id}><td><p className="font-bold text-[var(--ink)]">{company.name}</p><p className="mt-1 text-[10px] text-[var(--muted)]">{company.email ?? "Sin correo"} · {company.industry ?? "Sin sector"}</p></td><td><StatusBadge value={company.active ? company.access_status : "INACTIVE"} />{company.trial_ends_at && <p className="mt-1 text-[10px] text-[var(--muted)]">Hasta {formatDate(company.trial_ends_at)}</p>}</td><td><StatusBadge value={company.plan} /></td><td><p className="font-semibold">{company.users_count} usuarios · {company.assets_count} activos</p><p className="mt-1 text-[10px] text-[var(--muted)]">{company.open_incidents_count} incidencias · {company.open_work_orders_count} ordenes</p></td><td>{formatDate(company.last_activity_at, true)}</td><td><button className="icon-button" onClick={() => void openCompany(company)} aria-label={`Gestionar ${company.name}`} title="Gestionar empresa"><Settings2 size={17} /></button></td></tr>)}</tbody></table></div>
          <footer className="flex items-center justify-between border-t border-[var(--line)] px-4 py-3"><p className="text-xs text-[var(--muted)]">{pageData.total} empresas · pagina {pageData.page} de {pageData.pages}</p><div className="flex gap-2"><button className="icon-button" disabled={pageData.page <= 1} onClick={() => setPage((value) => value - 1)} aria-label="Pagina anterior"><ChevronLeft size={17} /></button><button className="icon-button" disabled={pageData.page >= pageData.pages} onClick={() => setPage((value) => value + 1)} aria-label="Pagina siguiente"><ChevronRight size={17} /></button></div></footer>
        </section>
      )}

      {loadingDetail && <div className="fixed inset-0 z-[80] grid place-items-center bg-black/30"><span className="loader" /></div>}
      <CompanyControlModal company={selected} onClose={() => setSelected(null)} onUpdate={updateCompany} onExtend={extendTrial} />
    </>
  );
}

function CompanyControlModal({ company, onClose, onUpdate, onExtend }: { company: OperatorCompanyDetail | null; onClose: () => void; onUpdate: (payload: Record<string, unknown>) => Promise<void>; onExtend: (days: number, reason: string) => Promise<void> }) {
  const [plan, setPlan] = useState<CompanyPlan>("TRIAL");
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus>("TRIAL");
  const [active, setActive] = useState(true);
  const [enabledModules, setEnabledModules] = useState<CompanyModule[]>([]);
  const [reason, setReason] = useState("");
  const [extendDays, setExtendDays] = useState("15");
  const [extendReason, setExtendReason] = useState("");
  const [limitOverrides, setLimitOverrides] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!company) return;
    setPlan(company.plan);
    setSubscriptionStatus(company.subscription_status);
    setActive(company.active);
    setEnabledModules(company.enabled_modules);
    setLimitOverrides(
      Object.fromEntries(
        Object.entries(company.limit_overrides).map(([key, value]) => [
          key,
          value === null ? "" : key === "storage_bytes" ? String(value / 1_000_000_000) : String(value),
        ]),
      ),
    );
    setReason("");
    setExtendReason("");
    setError("");
  }, [company]);

  function toggleModule(module: CompanyModule) {
    setEnabledModules((current) => {
      if (current.includes(module)) {
        if (module === "DOCUMENTS") return current.filter((item) => item !== "DOCUMENTS" && item !== "KNOWLEDGE");
        return current.filter((item) => item !== module);
      }
      const next = [...current, module];
      if (module === "KNOWLEDGE" && !next.includes("DOCUMENTS")) next.push("DOCUMENTS");
      return next;
    });
  }

  async function save(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    const normalizedLimits = Object.fromEntries(
      Object.entries(limitOverrides)
        .filter(([, value]) => value !== "")
        .map(([key, value]) => [key, key === "storage_bytes" ? Math.round(Number(value) * 1_000_000_000) : Number(value)]),
    );
    try { await onUpdate({ plan, subscription_status: subscriptionStatus, active, enabled_modules: enabledModules, limit_overrides: normalizedLimits, reason: reason || null }); }
    catch (saveError) { setError(saveError instanceof ApiError ? saveError.message : "No se pudo actualizar la empresa"); }
    finally { setSaving(false); }
  }

  async function extend(event: FormEvent) {
    event.preventDefault(); setSaving(true); setError("");
    try { await onExtend(Number(extendDays), extendReason); setExtendReason(""); }
    catch (extendError) { setError(extendError instanceof ApiError ? extendError.message : "No se pudo ampliar la prueba"); }
    finally { setSaving(false); }
  }

  return <Modal open={Boolean(company)} title={company?.name ?? "Empresa"} description="Control comercial y de disponibilidad. Los datos tecnicos permanecen fuera de este panel." onClose={onClose}>{company && <div className="overflow-y-auto"><div className="grid gap-4 border-b border-[var(--line)] p-5 sm:grid-cols-3"><Info label="Alta" value={formatDate(company.created_at)} /><Info label="Ultima actividad" value={formatDate(company.last_activity_at, true)} /><Info label="Contacto" value={company.email ?? "Sin correo"} /></div>{error && <div className="px-5 pt-5"><ErrorBanner message={error} /></div>}<form onSubmit={save}><div className="grid gap-4 p-5 sm:grid-cols-2"><Field label="Plan"><select className="field" value={plan} onChange={(event) => setPlan(event.target.value as CompanyPlan)}><option value="TRIAL">Prueba</option><option value="DEMO">Demo</option><option value="STARTER">Starter</option><option value="PRO">Pro</option><option value="INDUSTRIAL">Industrial</option><option value="ENTERPRISE">Enterprise</option><option value="PROFESSIONAL">Profesional (legacy)</option></select></Field><Field label="Estado de suscripcion"><select className="field" value={subscriptionStatus} onChange={(event) => setSubscriptionStatus(event.target.value as SubscriptionStatus)}><option value="TRIAL">Prueba</option><option value="ACTIVE">Activa</option><option value="SUSPENDED">Suspendida</option></select></Field><label className="flex items-center gap-3 rounded-md border border-[var(--line)] bg-[#fafcfb] px-4 py-3"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} /><span><strong className="block text-xs">Empresa habilitada</strong><span className="text-[10px] text-[var(--muted)]">Desactivar impide cualquier acceso.</span></span></label><Field label="Motivo del cambio"><input className="field" value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Obligatorio al suspender" /></Field></div><div className="border-y border-[var(--line)] px-5 py-4"><p className="text-xs font-bold">Modulos habilitados</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{modules.map((module) => <label key={module.key} className="flex items-center justify-between rounded-md border border-[var(--line)] px-3 py-2.5"><span className="text-xs font-semibold">{module.label}</span><input type="checkbox" className="module-toggle" checked={enabledModules.includes(module.key)} onChange={() => toggleModule(module.key)} /></label>)}</div></div><div className="border-b border-[var(--line)] px-5 py-4"><p className="text-xs font-bold">Limites y consumo</p><div className="mt-3 grid gap-3 sm:grid-cols-2">{limitFields.map((field) => { const usage = company.usage[field.key] ?? 0; const effective = company.limits[field.key]; const displayUsage = field.key === "storage_bytes" ? `${(usage / 1_000_000_000).toFixed(2)} GB` : String(usage); const displayLimit = effective === null ? "Sin limite" : field.key === "storage_bytes" ? `${(effective / 1_000_000_000).toFixed(0)} GB` : String(effective); return <label key={field.key} className="rounded-md border border-[var(--line)] p-3"><span className="flex items-center justify-between text-[11px] font-bold"><span>{field.label}</span><span className="text-[var(--muted)]">{displayUsage} / {displayLimit}</span></span><input className="field mt-2" type="number" min="0" step={field.key === "storage_bytes" ? "0.5" : "1"} value={limitOverrides[field.key] ?? ""} onChange={(event) => setLimitOverrides((current) => ({ ...current, [field.key]: event.target.value }))} placeholder="Usar limite del plan" /></label>; })}</div></div><div className="flex justify-end gap-2 px-5 py-4"><button type="button" className="button-secondary" onClick={onClose}>Cerrar</button><button className="button-primary" disabled={saving}>{saving ? "Guardando..." : "Guardar cambios"}</button></div></form><section className="border-t border-[var(--line)] bg-[#f8faf9] p-5"><div className="flex items-center gap-2"><TimerReset size={17} className="text-[var(--accent)]" /><h3 className="text-xs font-bold">Ampliar prueba</h3></div><form onSubmit={extend} className="mt-3 grid gap-3 sm:grid-cols-[110px_1fr_auto]"><input className="field" type="number" min="1" max="90" value={extendDays} onChange={(event) => setExtendDays(event.target.value)} aria-label="Dias de ampliacion" /><input className="field" value={extendReason} onChange={(event) => setExtendReason(event.target.value)} placeholder="Motivo de la ampliacion" minLength={5} required /><button className="button-secondary justify-center" disabled={saving}>Ampliar</button></form></section><section className="p-5"><div className="flex items-center gap-2"><Building2 size={17} className="text-[var(--accent)]" /><h3 className="text-xs font-bold">Administradores del cliente</h3></div><div className="mt-3 space-y-2">{company.administrators.map((admin) => <div key={admin.id} className="flex items-center justify-between rounded-md border border-[var(--line)] px-3 py-2.5"><div><p className="text-xs font-bold">{admin.full_name}</p><p className="mt-1 text-[10px] text-[var(--muted)]">{admin.email}</p></div><StatusBadge value={admin.active ? "ACTIVE" : "INACTIVE"} /></div>)}</div></section></div>}</Modal>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label><span className="field-label">{label}</span><div className="mt-2">{children}</div></label>; }
function Info({ label, value }: { label: string; value: string }) { return <div><p className="text-[10px] font-bold uppercase text-[var(--muted)]">{label}</p><p className="mt-1 truncate text-xs font-semibold">{value}</p></div>; }
