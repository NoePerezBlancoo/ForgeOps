"use client";

import { AlertTriangle, Boxes, Building2, ClipboardList, Factory, ShieldAlert, Timer, Users } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { useOperatorAuth } from "@/components/operator-auth-provider";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/format";
import type { CompanyModule, OperatorDashboard } from "@/lib/types";

const moduleNames: Record<CompanyModule, string> = {
  PREVENTIVE: "Preventivos",
  INVENTORY: "Inventario",
  DOCUMENTS: "Documentos",
  KNOWLEDGE: "IA documental",
};

export default function OperatorDashboardPage() {
  const { request } = useOperatorAuth();
  const [data, setData] = useState<OperatorDashboard | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setData(await request<OperatorDashboard>("/operator/dashboard"));
    } catch {
      setError("No se pudo cargar el estado de la plataforma");
    }
  }, [request]);

  useEffect(() => { void load(); }, [load]);

  if (!data && !error) return <LoadingBlock />;
  if (!data) return <ErrorBanner message={error} />;

  const attentionCount = data.expiring_trials + data.expired_trials + data.suspended_companies;
  return (
    <>
      <PageHeader title="Estado de ForgeOps" description="Seguimiento comercial y operativo de todos los espacios de empresa." actions={<button className="button-secondary" onClick={() => void load()}>Actualizar</button>} />
      {error && <ErrorBanner message={error} />}
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric label="Empresas" value={data.total_companies} icon={Building2} detail={`${data.active_customers} clientes activos`} />
        <Metric label="Pruebas activas" value={data.active_trials} icon={Timer} detail={`${data.expiring_trials} vencen en 7 dias`} tone={data.expiring_trials ? "warning" : "normal"} />
        <Metric label="Usuarios activos" value={data.active_users} icon={Users} detail="En todos los espacios" />
        <Metric label="Activos registrados" value={data.total_assets} icon={Boxes} detail="Equipos industriales" />
        <Metric label="Atencion requerida" value={attentionCount} icon={AlertTriangle} detail="Caducadas o suspendidas" tone={attentionCount ? "danger" : "normal"} />
      </section>

      <section className="mt-5 grid gap-5 xl:grid-cols-[1.55fr_0.85fr]">
        <article className="panel overflow-hidden">
          <header className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4">
            <div><h3 className="text-sm font-bold">Altas recientes</h3><p className="mt-1 text-xs text-[var(--muted)]">Ultimos espacios creados en la plataforma.</p></div>
            <Link href="/control/companies" className="text-xs font-bold text-[var(--accent)]">Ver cartera</Link>
          </header>
          {data.recent_companies.length === 0 ? <EmptyState title="Sin empresas" detail="Las nuevas altas apareceran aqui." /> : (
            <div className="table-wrap"><table className="data-table control-summary-table"><thead><tr><th>Empresa</th><th>Acceso</th><th>Equipo</th><th>Alta</th></tr></thead><tbody>{data.recent_companies.map((company) => <tr key={company.id}><td><p className="font-bold text-[var(--ink)]">{company.name}</p><p className="mt-1 text-[10px] text-[var(--muted)]">{company.industry ?? "Sector no indicado"}</p></td><td><StatusBadge value={company.active ? company.access_status : "INACTIVE"} /></td><td>{company.users_count} usuarios</td><td>{formatDate(company.created_at)}</td></tr>)}</tbody></table></div>
          )}
        </article>

        <div className="space-y-5">
          <article className="panel p-5">
            <h3 className="text-sm font-bold">Operacion agregada</h3>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <CompactMetric icon={ShieldAlert} label="Incidencias abiertas" value={data.open_incidents} />
              <CompactMetric icon={ClipboardList} label="Ordenes abiertas" value={data.open_work_orders} />
              <CompactMetric icon={Factory} label="Clientes activos" value={data.active_customers} />
              <CompactMetric icon={AlertTriangle} label="Pruebas caducadas" value={data.expired_trials} />
            </div>
          </article>
          <article className="panel p-5">
            <h3 className="text-sm font-bold">Adopcion de modulos</h3>
            <div className="mt-4 space-y-4">{Object.entries(data.module_adoption).map(([module, count]) => { const percent = data.total_companies ? Math.round((count / data.total_companies) * 100) : 0; return <div key={module}><div className="flex justify-between text-xs"><span className="font-semibold text-[var(--ink-soft)]">{moduleNames[module as CompanyModule]}</span><span className="font-bold">{count} · {percent}%</span></div><div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#e8ecea]"><div className="h-full bg-[var(--accent)]" style={{ width: `${percent}%` }} /></div></div>; })}</div>
          </article>
        </div>
      </section>
    </>
  );
}

function Metric({ label, value, icon: Icon, detail, tone = "normal" }: { label: string; value: number; icon: typeof Building2; detail: string; tone?: "normal" | "warning" | "danger" }) {
  const colors = tone === "danger" ? "bg-red-50 text-red-700" : tone === "warning" ? "bg-amber-50 text-amber-700" : "bg-cyan-50 text-cyan-800";
  return <article className="panel min-w-0 p-4"><div className={`grid size-9 place-items-center rounded-md ${colors}`}><Icon size={18} /></div><p className="mt-4 text-2xl font-bold">{value}</p><p className="mt-1 text-xs font-bold text-[var(--ink-soft)]">{label}</p><p className="mt-1 truncate text-[10px] text-[var(--muted)]">{detail}</p></article>;
}

function CompactMetric({ icon: Icon, label, value }: { icon: typeof ShieldAlert; label: string; value: number }) {
  return <div className="rounded-md border border-[var(--line)] bg-[#fafcfb] p-3"><Icon size={16} className="text-[var(--accent)]" /><p className="mt-3 text-lg font-bold">{value}</p><p className="mt-1 text-[10px] font-semibold leading-4 text-[var(--muted)]">{label}</p></div>;
}
