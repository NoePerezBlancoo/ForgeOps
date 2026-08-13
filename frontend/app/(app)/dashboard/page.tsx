"use client";

import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Boxes,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Compass,
  Download,
  PackageSearch,
  Plus,
  RefreshCw,
  TimerOff,
  Users,
  Wrench,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAuth } from "@/components/auth-provider";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { formatDate, initials, labelFor } from "@/lib/format";
import type { DashboardData } from "@/lib/types";

type ReportPeriod = 7 | 30 | 90 | 365;

const periods: Array<{ value: ReportPeriod; label: string }> = [
  { value: 7, label: "7 dias" },
  { value: 30, label: "30 dias" },
  { value: 90, label: "90 dias" },
  { value: 365, label: "1 ano" },
];

const statusColors: Record<string, string> = {
  ACTIVE: "#21855b",
  STOPPED: "#c83e45",
  MAINTENANCE: "#c57a0a",
  OUT_OF_SERVICE: "#718082",
  OPEN: "#007c83",
  ASSIGNED: "#449ba0",
  IN_PROGRESS: "#c57a0a",
  WAITING: "#879291",
  PENDING_VALIDATION: "#a6600a",
  COMPLETED: "#21855b",
  CLOSED: "#365c51",
  CANCELLED: "#b5bdbc",
};

export default function DashboardPage() {
  const { request, download: downloadFile, user } = useAuth();
  const { isModuleEnabled, onboarding, scopedPath, selectedPlant } = useWorkspace();
  const [data, setData] = useState<DashboardData | null>(null);
  const [period, setPeriod] = useState<ReportPeriod>(30);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    request<DashboardData>(scopedPath(`/dashboard?period_days=${period}`))
      .then((loaded) => {
        if (active) setData(loaded);
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el informe operativo");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [period, request, scopedPath]);

  async function exportReport() {
    setExporting(true);
    setError("");
    try {
      const blob = await downloadFile(scopedPath(`/dashboard/export?period_days=${period}`));
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `forgeops-operaciones-${new Date().toISOString().slice(0, 10)}.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo exportar el informe");
    } finally {
      setExporting(false);
    }
  }

  if (!data && loading) return <LoadingBlock />;
  const reportPeriod = data?.period_days ?? period;

  const metrics = data ? [
    { label: "Activos parados", value: data.stopped_assets, icon: TimerOff, tone: "bg-red-50 text-red-700" },
    { label: "Incidencias abiertas", value: data.open_incidents, icon: AlertTriangle, tone: "bg-orange-50 text-orange-700" },
    { label: "OT vencidas", value: data.overdue_work_orders, icon: Clock3, tone: "bg-red-50 text-red-700" },
    { label: "OT en curso", value: data.in_progress_work_orders, icon: Wrench, tone: "bg-amber-50 text-amber-800" },
    { label: `Parada en ${reportPeriod} dias`, value: `${data.downtime_hours} h`, icon: Activity, tone: "bg-cyan-50 text-cyan-800" },
    { label: `MTTR · ${data.resolved_incidents} resueltas`, value: data.mttr_hours === null ? "Sin datos" : `${data.mttr_hours} h`, icon: CheckCircle2, tone: "bg-emerald-50 text-emerald-700" },
    isModuleEnabled("PREVENTIVE") ? { label: "Preventivos vencidos", value: data.overdue_preventive_count, icon: CalendarClock, tone: "bg-orange-50 text-orange-700" } : null,
    isModuleEnabled("INVENTORY") ? { label: "Repuestos bajo minimo", value: data.low_stock_items, icon: PackageSearch, tone: "bg-slate-100 text-slate-700" } : null,
  ].filter((metric): metric is NonNullable<typeof metric> => metric !== null) : [];

  const orderChart = data?.work_order_statuses.map((item) => ({ ...item, name: labelFor(item.label) })) ?? [];
  const incidentTrend = data?.incident_trend.map((item) => ({
    ...item,
    name: new Date(`${item.label}T00:00:00`).toLocaleDateString("es-ES", { day: "2-digit", month: "short" }),
  })) ?? [];

  return (
    <>
      <PageHeader
        title={`Buenos dias, ${user?.full_name.split(" ")[0] ?? "equipo"}`}
        description={`Prioridades de ${selectedPlant?.name ?? user?.company.name ?? "la empresa"} y carga actual de mantenimiento.`}
        actions={(
          <>
            <Link href="/work-orders" className="button-secondary"><Wrench size={16} /> Ver ordenes</Link>
            {user?.role !== "VIEWER" && <Link href="/incidents?new=1" className="button-primary"><Plus size={16} /> Registrar incidencia</Link>}
          </>
        )}
      />
      {error && <ErrorBanner message={error} />}

      {onboarding && onboarding.percent < 100 && (
        <section className="panel mb-4 flex flex-col gap-4 border-l-4 border-l-[var(--accent)] p-4 lg:flex-row lg:items-center">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Compass size={20} /></span>
            <div><p className="text-sm font-bold">Continua la puesta en marcha</p><p className="mt-1 text-xs text-[var(--muted)]">{onboarding.completed} de {onboarding.total} pasos completados.</p></div>
          </div>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-[#e8ecea]"><div className="h-full bg-[var(--accent)]" style={{ width: `${onboarding.percent}%` }} /></div>
          <Link className="button-secondary justify-center" href="/getting-started">Abrir guia <ArrowRight size={15} /></Link>
        </section>
      )}

      <section className="mb-4 flex flex-col gap-3 border-y border-[var(--line)] bg-white px-3 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="grid grid-cols-4 rounded-md border border-[var(--line)] bg-[#f4f7f6] p-1" aria-label="Periodo del informe">
          {periods.map((item) => (
            <button
              key={item.value}
              className={`min-h-11 rounded px-3 text-xs font-bold ${period === item.value ? "bg-white text-[var(--accent)] shadow-sm" : "text-[var(--muted)]"}`}
              onClick={() => setPeriod(item.value)}
              aria-pressed={period === item.value}
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="flex items-center justify-between gap-3 sm:justify-end">
          <p className="text-[11px] font-semibold text-[var(--muted)]">Actualizado {data ? formatDate(data.generated_at, true) : ""}</p>
          <button className="button-secondary" onClick={() => void exportReport()} disabled={exporting || loading}>
            {exporting ? <RefreshCw className="animate-spin" size={15} /> : <Download size={15} />} CSV
          </button>
        </div>
      </section>

      {data && (
        <>
          <section className={`grid grid-cols-2 gap-3 lg:grid-cols-4 ${loading ? "opacity-60" : ""}`} aria-busy={loading}>
            {metrics.map((metric) => {
              const Icon = metric.icon;
              return (
                <article key={metric.label} className="panel min-h-29 p-4">
                  <div className={`grid size-8 place-items-center rounded-md ${metric.tone}`}><Icon size={17} /></div>
                  <p className="mt-3 text-xl font-bold text-[var(--ink)] sm:text-2xl">{metric.value}</p>
                  <p className="mt-1 text-[11px] font-semibold leading-4 text-[var(--muted)]">{metric.label}</p>
                </article>
              );
            })}
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-2">
            <ChartPanel title="Tendencia de incidencias" detail={`Altas registradas en los ultimos ${reportPeriod} dias`}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={incidentTrend} margin={{ top: 8, right: 8, left: -25, bottom: 0 }}>
                  <CartesianGrid stroke="#e8ecea" vertical={false} />
                  <XAxis dataKey="name" interval="preserveStartEnd" minTickGap={24} tick={{ fontSize: 10, fill: "#718082" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#718082" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ border: "1px solid #dce2df", borderRadius: 5, fontSize: 12 }} />
                  <Line type="monotone" dataKey="value" name="Incidencias" stroke="#007c83" strokeWidth={2.5} dot={reportPeriod <= 30 ? { r: 2 } : false} activeDot={{ r: 5 }} />
                </LineChart>
              </ResponsiveContainer>
            </ChartPanel>

            <ChartPanel title="Carga de ordenes" detail="Distribucion actual por estado operativo">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={orderChart} margin={{ top: 8, right: 8, left: -25, bottom: 0 }}>
                  <CartesianGrid stroke="#e8ecea" vertical={false} />
                  <XAxis dataKey="name" interval={0} tick={{ fontSize: 9, fill: "#718082" }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#718082" }} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#f3f5f4" }} contentStyle={{ border: "1px solid #dce2df", borderRadius: 5, fontSize: 12 }} />
                  <Bar dataKey="value" name="Ordenes" radius={[3, 3, 0, 0]}>{orderChart.map((entry) => <Cell key={entry.label} fill={statusColors[entry.label] ?? "#007c83"} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartPanel>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-2">
            <ListPanel title="Activos con mayor impacto" detail={`Parada e incidencias en ${reportPeriod} dias`} empty={data.top_assets.length === 0}>
              {data.top_assets.map((asset, index) => (
                <Link key={asset.asset_id} href={`/assets?search=${encodeURIComponent(asset.asset_code)}`} className="flex min-h-16 items-center gap-3 px-4 py-3 hover:bg-[#fafcfb] sm:px-5">
                  <span className="grid size-8 shrink-0 place-items-center rounded-md bg-slate-100 text-xs font-bold text-[var(--ink-soft)]">{index + 1}</span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{asset.asset_code} · {asset.asset_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{asset.incidents} incidencias</p></div>
                  <strong className="shrink-0 text-sm text-red-700">{asset.downtime_hours} h</strong>
                </Link>
              ))}
            </ListPanel>

            <ListPanel title="Carga del equipo" detail="Participacion en ordenes activas" empty={data.technician_workload.length === 0}>
              {data.technician_workload.map((technician) => (
                <div key={technician.user_id} className="flex min-h-16 items-center gap-3 px-4 py-3 sm:px-5">
                  <span className="grid size-8 shrink-0 place-items-center rounded-md bg-[var(--ink)] text-[10px] font-bold text-white">{initials(technician.full_name)}</span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{technician.full_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{technician.in_progress_work_orders} en curso · {technician.active_sessions} sesiones abiertas</p></div>
                  <span className="inline-flex shrink-0 items-center gap-1.5 text-sm font-bold"><Users size={14} /> {technician.active_work_orders}</span>
                </div>
              ))}
            </ListPanel>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-2">
            <ListPanel title="Incidencias recientes" detail="Ultimos eventos registrados en planta" empty={data.recent_incidents.length === 0}>
              {data.recent_incidents.map((incident) => (
                <Link key={incident.id} href={`/incidents?incident=${incident.id}`} className="flex min-h-16 items-center gap-3 px-4 py-3 hover:bg-[#fafcfb] sm:px-5">
                  <span className="grid size-8 shrink-0 place-items-center rounded-md bg-red-50 text-red-700"><AlertTriangle size={16} /></span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{incident.title}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{incident.asset_code} · {formatDate(incident.reported_at, true)}</p></div>
                  <StatusBadge value={incident.priority} />
                </Link>
              ))}
            </ListPanel>

            <ListPanel title="Trabajo programado" detail="Siguientes intervenciones abiertas" empty={data.upcoming_work_orders.length === 0}>
              {data.upcoming_work_orders.map((order) => (
                <Link key={order.id} href={`/work-orders?order=${order.id}`} className="flex min-h-16 items-center gap-3 px-4 py-3 hover:bg-[#fafcfb] sm:px-5">
                  <span className="grid size-8 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Wrench size={16} /></span>
                  <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{order.title}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{order.number} · {order.asset_code} · {formatDate(order.scheduled_date)}</p></div>
                  <StatusBadge value={order.status} />
                </Link>
              ))}
            </ListPanel>
          </section>

          <section className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-md border border-[var(--line)] bg-[var(--line)]">
            <Summary label="Activos operativos" value={data.active_assets} icon={<Boxes size={15} />} />
            <Summary label="OT finalizadas" value={data.completed_work_orders} icon={<CheckCircle2 size={15} />} />
            <Summary label="Preventivos proximos" value={data.upcoming_preventive_count} icon={<CalendarClock size={15} />} />
          </section>
        </>
      )}
    </>
  );
}

function ChartPanel({ title, detail, children }: { title: string; detail: string; children: React.ReactNode }) {
  return <article className="panel p-4 sm:p-5"><header><h2 className="text-sm font-bold">{title}</h2><p className="mt-1 text-xs text-[var(--muted)]">{detail}</p></header><div className="mt-4 h-60 w-full">{children}</div></article>;
}

function ListPanel({ title, detail, empty, children }: { title: string; detail: string; empty: boolean; children: React.ReactNode }) {
  return <article className="panel overflow-hidden"><header className="border-b border-[var(--line)] px-4 py-4 sm:px-5"><h2 className="text-sm font-bold">{title}</h2><p className="mt-1 text-xs text-[var(--muted)]">{detail}</p></header>{empty ? <p className="px-5 py-8 text-center text-sm text-[var(--muted)]">Sin datos para este alcance.</p> : <div className="divide-y divide-[var(--line)]">{children}</div>}</article>;
}

function Summary({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  return <div className="min-w-0 bg-white px-3 py-3 sm:px-4"><p className="flex items-center gap-2 text-[10px] font-bold uppercase text-[var(--muted)]">{icon}<span className="truncate">{label}</span></p><p className="mt-2 text-lg font-bold">{value}</p></div>;
}
