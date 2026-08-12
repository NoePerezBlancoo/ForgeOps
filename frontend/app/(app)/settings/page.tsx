"use client";

import { Activity, Clock3, KeyRound, Laptop, LogOut, ShieldCheck } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import { formatDate, initials, labelFor } from "@/lib/format";
import type { AuditEvent, AuditSummary, AuthSession } from "@/lib/types";

type SettingsView = "security" | "audit";

export default function SettingsPage() {
  const { request, user, logout } = useAuth();
  const router = useRouter();
  const [view, setView] = useState<SettingsView>("security");
  const [sessions, setSessions] = useState<AuthSession[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [passwords, setPasswords] = useState({ current_password: "", password: "", confirmation: "" });
  const canAudit = user && ["SUPER_ADMIN", "ADMIN"].includes(user.role);

  const loadSecurity = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setSessions(await request<AuthSession[]>("/auth/sessions"));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las sesiones");
    } finally {
      setLoading(false);
    }
  }, [request]);

  const loadAudit = useCallback(async () => {
    if (!canAudit) return;
    setLoading(true);
    setError("");
    try {
      const [eventData, summaryData] = await Promise.all([
        request<AuditEvent[]>("/audit-events?limit=100"),
        request<AuditSummary>("/audit-events/summary"),
      ]);
      setEvents(eventData);
      setSummary(summaryData);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar la auditoria");
    } finally {
      setLoading(false);
    }
  }, [canAudit, request]);

  useEffect(() => {
    if (view === "audit") void loadAudit();
    else void loadSecurity();
  }, [loadAudit, loadSecurity, view]);

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (passwords.password !== passwords.confirmation) {
      setError("La confirmacion no coincide con la nueva contrasena");
      return;
    }
    setSaving(true);
    try {
      await request<void>("/auth/password", { method: "POST", body: JSON.stringify({ current_password: passwords.current_password, password: passwords.password }) });
      await logout();
      router.replace("/login");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cambiar la contrasena");
    } finally {
      setSaving(false);
    }
  }

  async function revokeOthers() {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const result = await request<{ revoked: number }>("/auth/sessions/revoke-others", { method: "POST" });
      setNotice(result.revoked ? `${result.revoked} sesiones adicionales cerradas` : "No habia otras sesiones activas");
      await loadSecurity();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cerrar las sesiones");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Seguridad y auditoria" description="Protege tu acceso y revisa la actividad administrativa de la empresa." />
      <div className="mb-5 inline-flex rounded-md border border-[var(--line)] bg-white p-1">
        <button className={`flex min-h-9 items-center gap-2 rounded px-3 text-xs font-bold ${view === "security" ? "bg-[var(--ink)] text-white" : "text-[var(--muted)]"}`} onClick={() => setView("security")}><ShieldCheck size={15} /> Mi seguridad</button>
        {canAudit && <button className={`flex min-h-9 items-center gap-2 rounded px-3 text-xs font-bold ${view === "audit" ? "bg-[var(--ink)] text-white" : "text-[var(--muted)]"}`} onClick={() => setView("audit")}><Activity size={15} /> Auditoria</button>}
      </div>
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      {loading ? <LoadingBlock /> : view === "security" ? (
        <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
          <section className="panel overflow-hidden">
            <header className="border-b border-[var(--line)] px-5 py-4"><h3 className="text-sm font-bold">Perfil de acceso</h3><p className="mt-1 text-xs text-[var(--muted)]">Identidad y nivel de autorizacion actual.</p></header>
            <div className="p-5">
              <div className="flex items-center gap-4"><div className="grid size-12 place-items-center rounded-md bg-[var(--ink)] text-sm font-bold text-white">{initials(user?.full_name ?? "")}</div><div><p className="font-bold">{user?.full_name}</p><p className="mt-1 text-xs text-[var(--muted)]">{user?.email}</p></div></div>
              <dl className="mt-6 divide-y divide-[var(--line)] text-xs"><div className="flex justify-between py-3"><dt className="text-[var(--muted)]">Rol</dt><dd className="font-bold">{user ? labelFor(user.role) : ""}</dd></div><div className="flex justify-between py-3"><dt className="text-[var(--muted)]">Empresa</dt><dd className="font-bold">{user?.company.name}</dd></div><div className="flex justify-between py-3"><dt className="text-[var(--muted)]">Ultimo acceso</dt><dd className="font-bold">{user?.last_login_at ? formatDate(user.last_login_at, true) : "Sesion actual"}</dd></div></dl>
            </div>
          </section>
          <section className="panel overflow-hidden">
            <header className="border-b border-[var(--line)] px-5 py-4"><h3 className="text-sm font-bold">Cambiar contrasena</h3><p className="mt-1 text-xs text-[var(--muted)]">Al guardar se cerraran todas las sesiones y deberas volver a entrar.</p></header>
            <form onSubmit={changePassword}><div className="grid gap-4 p-5 sm:grid-cols-2"><div className="sm:col-span-2"><Field label="Contrasena actual"><input className="field" type="password" value={passwords.current_password} onChange={(event) => setPasswords({ ...passwords, current_password: event.target.value })} required /></Field></div><Field label="Nueva contrasena"><input className="field" type="password" value={passwords.password} onChange={(event) => setPasswords({ ...passwords, password: event.target.value })} minLength={10} required /></Field><Field label="Confirmacion"><input className="field" type="password" value={passwords.confirmation} onChange={(event) => setPasswords({ ...passwords, confirmation: event.target.value })} minLength={10} required /></Field><p className="text-[11px] leading-5 text-[var(--muted)] sm:col-span-2">Minimo 10 caracteres con mayuscula, minuscula y numero.</p></div><footer className="flex justify-end border-t border-[var(--line)] px-5 py-4"><button className="button-primary" disabled={saving}><KeyRound size={16} /> Actualizar contrasena</button></footer></form>
          </section>
          <section className="panel overflow-hidden xl:col-span-2">
            <header className="flex items-center justify-between border-b border-[var(--line)] px-5 py-4"><div><h3 className="text-sm font-bold">Sesiones activas</h3><p className="mt-1 text-xs text-[var(--muted)]">Accesos renovables asociados a tu cuenta.</p></div><button className="button-secondary" onClick={revokeOthers} disabled={saving}><LogOut size={16} /> Cerrar las demas</button></header>
            {sessions.length === 0 ? <EmptyState title="No hay sesiones renovables" detail="La sesion actual caducara al terminar el token de acceso." /> : <div className="divide-y divide-[var(--line)]">{sessions.map((session) => <div key={session.id} className="flex items-center gap-4 px-5 py-4"><div className="grid size-9 place-items-center rounded-md bg-slate-100 text-slate-700"><Laptop size={17} /></div><div className="min-w-0 flex-1"><p className="text-xs font-bold">{session.current ? "Esta sesion" : "Sesion web"}</p><p className="mt-1 text-[11px] text-[var(--muted)]">Iniciada {formatDate(session.created_at, true)} · expira {formatDate(session.expires_at, true)}</p></div>{session.current && <span className="status-badge badge-success">Actual</span>}</div>)}</div>}
          </section>
        </div>
      ) : (
        <>
          <section className="mb-5 grid gap-3 sm:grid-cols-4"><Metric icon={Activity} label="Eventos registrados" value={summary?.total_events ?? 0} /><Metric icon={Laptop} label="Sesiones activas" value={summary?.active_sessions ?? 0} /><Metric icon={ShieldCheck} label="Administradores" value={summary?.administrators ?? 0} /><Metric icon={Clock3} label="Ultimo evento" value={summary?.last_event_at ? formatDate(summary.last_event_at, true) : "Sin actividad"} /></section>
          <section className="panel overflow-hidden"><header className="border-b border-[var(--line)] px-5 py-4"><h3 className="text-sm font-bold">Registro administrativo</h3><p className="mt-1 text-xs text-[var(--muted)]">Cambios de configuracion, accesos, usuarios y plantas.</p></header>{events.length === 0 ? <EmptyState title="Todavia no hay actividad" detail="Los cambios administrativos apareceran aqui." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Evento</th><th>Ambito</th><th>Responsable</th><th>Fecha</th><th>IP</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td><p className="font-bold text-[var(--ink)]">{event.summary}</p><p className="mt-1 text-[10px] font-bold uppercase text-[var(--accent)]">{auditAction(event.action)}</p></td><td>{event.entity_type}</td><td>{event.actor?.full_name ?? "Sistema"}</td><td>{formatDate(event.created_at, true)}</td><td>{event.ip_address ?? "Interna"}</td></tr>)}</tbody></table></div>}</section>
        </>
      )}
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function Metric({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string | number }) {
  return <article className="panel flex min-h-24 items-center gap-3 p-4"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Icon size={17} /></div><div className="min-w-0"><p className="text-sm font-bold leading-5">{value}</p><p className="mt-1 text-[10px] font-bold uppercase text-[var(--muted)]">{label}</p></div></article>;
}

function auditAction(value: string): string {
  return { LOGIN: "Inicio de sesion", CREATE: "Creacion", UPDATE: "Actualizacion", ACTIVATE: "Activacion", DEACTIVATE: "Desactivacion", PASSWORD_RESET: "Restablecimiento", PASSWORD_CHANGE: "Cambio de contrasena", SESSIONS_REVOKE: "Cierre de sesiones" }[value] ?? value;
}
