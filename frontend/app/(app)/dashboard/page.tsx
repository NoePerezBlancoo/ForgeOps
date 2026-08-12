"use client";

import {
  Activity,
  AlertTriangle,
  Boxes,
  CheckCircle2,
  Clock3,
  Factory,
  TimerOff,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAuth } from "@/components/auth-provider";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { DashboardData } from "@/lib/types";

const statusColors: Record<string, string> = {
  ACTIVE: "#21855b",
  STOPPED: "#c83e45",
  MAINTENANCE: "#c57a0a",
  OUT_OF_SERVICE: "#718082",
  OPEN: "#007c83",
  ASSIGNED: "#449ba0",
  IN_PROGRESS: "#c57a0a",
  WAITING: "#879291",
  COMPLETED: "#21855b",
  CANCELLED: "#b5bdbc",
  CRITICAL: "#c83e45",
  HIGH: "#e37a26",
  MEDIUM: "#178b94",
  LOW: "#8b9795",
};

export default function DashboardPage() {
  const { request, user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    request<DashboardData>("/dashboard")
      .then(setData)
      .catch((requestError) =>
        setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el dashboard"),
      );
  }, [request]);

  if (!data && !error) return <LoadingBlock />;

  const metrics = data
    ? [
        { label: "Activos operativos", value: data.active_assets, icon: Boxes, tone: "text-emerald-700 bg-emerald-50" },
        { label: "Activos parados", value: data.stopped_assets, icon: TimerOff, tone: "text-red-700 bg-red-50" },
        { label: "Incidencias abiertas", value: data.open_incidents, icon: AlertTriangle, tone: "text-orange-700 bg-orange-50" },
        { label: "Ordenes pendientes", value: data.pending_work_orders, icon: Clock3, tone: "text-cyan-800 bg-cyan-50" },
        { label: "Ordenes en curso", value: data.in_progress_work_orders, icon: Wrench, tone: "text-amber-700 bg-amber-50" },
        { label: "Completadas", value: data.completed_work_orders, icon: CheckCircle2, tone: "text-emerald-700 bg-emerald-50" },
        { label: "Parada ultimos 30 dias", value: `${data.downtime_hours} h`, icon: Activity, tone: "text-violet-700 bg-violet-50" },
        { label: "Criticas abiertas", value: data.critical_incidents, icon: Factory, tone: "text-red-700 bg-red-50" },
      ]
    : [];

  const assetChart = data?.asset_statuses.map((item) => ({ ...item, name: labelFor(item.label) })) ?? [];
  const workOrderChart = data?.work_order_statuses.map((item) => ({ ...item, name: labelFor(item.label) })) ?? [];

  return (
    <>
      <PageHeader
        title={`Buenos dias, ${user?.full_name.split(" ")[0] ?? "equipo"}`}
        description="Estado operativo de MetalWorks Demo S.L. y carga actual del equipo de mantenimiento."
      />
      {error && <ErrorBanner message={error} />}
      {data && (
        <>
          <section className="grid grid-cols-2 gap-3 lg:grid-cols-4 xl:grid-cols-8">
            {metrics.map((metric) => {
              const Icon = metric.icon;
              return (
                <article key={metric.label} className="panel min-h-31 p-4 xl:col-span-2">
                  <div className={`grid size-8 place-items-center rounded-md ${metric.tone}`}>
                    <Icon size={17} />
                  </div>
                  <p className="mt-4 text-2xl font-bold text-[var(--ink)]">{metric.value}</p>
                  <p className="mt-1 text-[11px] font-semibold leading-4 text-[var(--muted)]">{metric.label}</p>
                </article>
              );
            })}
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
            <article className="panel p-5">
              <div className="mb-5">
                <h3 className="text-sm font-bold">Carga de ordenes</h3>
                <p className="mt-1 text-xs text-[var(--muted)]">Distribucion por estado operativo</p>
              </div>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={workOrderChart} margin={{ top: 5, right: 5, left: -22, bottom: 0 }}>
                    <CartesianGrid stroke="#e8ecea" vertical={false} />
                    <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#718082" }} axisLine={false} tickLine={false} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#718082" }} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{ fill: "#f3f5f4" }} contentStyle={{ border: "1px solid #dce2df", borderRadius: 5, fontSize: 12 }} />
                    <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                      {workOrderChart.map((entry) => <Cell key={entry.label} fill={statusColors[entry.label] ?? "#007c83"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="panel p-5">
              <div className="mb-2">
                <h3 className="text-sm font-bold">Disponibilidad de activos</h3>
                <p className="mt-1 text-xs text-[var(--muted)]">Situacion actual de planta</p>
              </div>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={assetChart} dataKey="value" nameKey="name" innerRadius={48} outerRadius={72} paddingAngle={3}>
                      {assetChart.map((entry) => <Cell key={entry.label} fill={statusColors[entry.label] ?? "#718082"} />)}
                    </Pie>
                    <Tooltip contentStyle={{ border: "1px solid #dce2df", borderRadius: 5, fontSize: 12 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                {assetChart.map((entry) => (
                  <div key={entry.label} className="flex items-center gap-2 text-[11px] font-semibold text-[var(--ink-soft)]">
                    <span className="size-2 rounded-full" style={{ backgroundColor: statusColors[entry.label] }} />
                    <span className="truncate">{entry.name}</span>
                    <strong className="ml-auto text-[var(--ink)]">{entry.value}</strong>
                  </div>
                ))}
              </div>
            </article>
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-2">
            <article className="panel overflow-hidden">
              <header className="border-b border-[var(--line)] px-5 py-4">
                <h3 className="text-sm font-bold">Incidencias recientes</h3>
                <p className="mt-1 text-xs text-[var(--muted)]">Ultimos eventos registrados en planta</p>
              </header>
              <div className="divide-y divide-[var(--line)]">
                {data.recent_incidents.map((incident) => (
                  <div key={incident.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="grid size-9 shrink-0 place-items-center rounded-md bg-red-50 text-red-700">
                      <AlertTriangle size={17} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-bold text-[var(--ink)]">{incident.title}</p>
                      <p className="mt-1 text-[11px] text-[var(--muted)]">{incident.asset_code} · {formatDate(incident.reported_at, true)}</p>
                    </div>
                    <StatusBadge value={incident.priority} />
                  </div>
                ))}
              </div>
            </article>

            <article className="panel overflow-hidden">
              <header className="border-b border-[var(--line)] px-5 py-4">
                <h3 className="text-sm font-bold">Trabajo programado</h3>
                <p className="mt-1 text-xs text-[var(--muted)]">Siguientes intervenciones abiertas</p>
              </header>
              <div className="divide-y divide-[var(--line)]">
                {data.upcoming_work_orders.map((order) => (
                  <div key={order.id} className="flex items-center gap-3 px-5 py-3.5">
                    <div className="grid size-9 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800">
                      <ClipboardListIcon />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-bold text-[var(--ink)]">{order.title}</p>
                      <p className="mt-1 text-[11px] text-[var(--muted)]">{order.number} · {order.asset_code} · {formatDate(order.scheduled_date)}</p>
                    </div>
                    <StatusBadge value={order.status} />
                  </div>
                ))}
              </div>
            </article>
          </section>
        </>
      )}
    </>
  );
}

function ClipboardListIcon() {
  return <Wrench size={17} />;
}

