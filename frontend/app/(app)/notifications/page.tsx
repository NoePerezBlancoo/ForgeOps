"use client";

import { Bell, CheckCheck, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { NotificationList } from "@/lib/types";

export default function NotificationsPage() {
  const { request } = useAuth();
  const [data, setData] = useState<NotificationList>({ items: [], total: 0, unread: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await request<NotificationList>("/notifications?limit=100"));
      setError("");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las notificaciones");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => { void load(); }, [load]);

  async function markAll() {
    try {
      await request("/notifications/read-all", { method: "POST" });
      await load();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron actualizar las notificaciones");
    }
  }

  async function markRead(id: string) {
    try {
      await request(`/notifications/${id}/read`, { method: "PATCH" });
      setData((current) => ({
        ...current,
        unread: Math.max(0, current.unread - 1),
        items: current.items.map((item) => item.id === id ? { ...item, read_at: new Date().toISOString() } : item),
      }));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar la notificacion");
    }
  }

  return (
    <>
      <PageHeader title="Notificaciones" description="Trabajos asignados y avisos operativos que requieren tu atencion." actions={data.unread > 0 ? <button className="button-secondary" onClick={markAll}><CheckCheck size={17} /> Marcar todo como leido</button> : undefined} />
      {error && <ErrorBanner message={error} />}
      {loading ? <LoadingBlock /> : data.items.length === 0 ? <section className="panel"><EmptyState title="Todo al dia" detail="Los nuevos avisos operativos apareceran aqui." /></section> : (
        <section className="panel overflow-hidden">
          <div className="divide-y divide-[var(--line)]">
            {data.items.map((notification) => (
              <article key={notification.id} className={`flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:px-5 ${notification.read_at ? "bg-white" : "bg-cyan-50/35"}`}>
                <div className="grid size-9 shrink-0 place-items-center rounded-md bg-slate-100 text-[var(--ink-soft)]"><Bell size={17} /></div>
                <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="text-sm font-bold">{notification.title}</h2>{!notification.read_at && <span className="size-2 rounded-full bg-[var(--accent)]" />}<span className="text-[10px] font-bold uppercase text-[var(--muted)]">{labelFor(notification.type)}</span></div><p className="mt-1 text-sm leading-6 text-[var(--muted)]">{notification.body}</p><p className="mt-1 text-[11px] font-semibold text-[var(--muted)]">{formatDate(notification.created_at, true)}</p></div>
                <div className="flex shrink-0 items-center gap-2">{!notification.read_at && <button className="button-secondary" onClick={() => void markRead(notification.id)}>Marcar leida</button>}{notification.href && <Link className="icon-button" href={notification.href} onClick={() => !notification.read_at && void markRead(notification.id)} aria-label="Abrir elemento relacionado" title="Abrir"><ExternalLink size={16} /></Link>}</div>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
