"use client";

import { Bell, CalendarClock, CheckCheck, ClipboardList, Clock3, PackageX, ShieldAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { AppNotification, NotificationList, NotificationType } from "@/lib/types";

const notificationIcons: Record<NotificationType, typeof Bell> = {
  WORK_ORDER_ASSIGNED: ClipboardList,
  CRITICAL_INCIDENT: ShieldAlert,
  PREVENTIVE_DUE: CalendarClock,
  PREVENTIVE_OVERDUE: Clock3,
  LOW_STOCK: PackageX,
  TRIAL_EXPIRING: Clock3,
};

export function NotificationCenter() {
  const { request } = useAuth();
  const router = useRouter();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<NotificationList>({ items: [], total: 0, unread: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      setData(await request<NotificationList>("/notifications?limit=8"));
      setError("");
    } catch (requestError) {
      if (!silent) {
        setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar los avisos");
      }
    } finally {
      if (!silent) setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void load(true);
    const interval = window.setInterval(() => void load(true), 60_000);
    return () => window.clearInterval(interval);
  }, [load]);

  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, []);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) await load();
  }

  async function openNotification(notification: AppNotification) {
    try {
      if (!notification.read_at) {
        await request(`/notifications/${notification.id}/read`, { method: "PATCH" });
        setData((current) => ({
          ...current,
          unread: Math.max(0, current.unread - 1),
          items: current.items.map((item) => item.id === notification.id ? { ...item, read_at: new Date().toISOString() } : item),
        }));
      }
      setOpen(false);
      if (notification.href) router.push(notification.href);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar el aviso");
    }
  }

  async function markAllRead() {
    try {
      await request("/notifications/read-all", { method: "POST" });
      setData((current) => ({
        ...current,
        unread: 0,
        items: current.items.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })),
      }));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron actualizar los avisos");
    }
  }

  return (
    <div className="relative" ref={rootRef}>
      <button className="icon-button relative" onClick={toggle} aria-label="Notificaciones" aria-expanded={open} title="Notificaciones">
        <Bell size={18} />
        {data.unread > 0 && <span className="absolute -right-1 -top-1 grid min-w-4 place-items-center rounded-full bg-red-600 px-1 text-[9px] font-bold leading-4 text-white">{data.unread > 9 ? "9+" : data.unread}</span>}
      </button>
      {open && (
        <section className="absolute right-0 top-12 z-50 w-[min(23rem,calc(100vw-2rem))] overflow-hidden rounded-md border border-[var(--line)] bg-white shadow-2xl" aria-label="Centro de notificaciones">
          <header className="flex items-center justify-between border-b border-[var(--line)] px-4 py-3">
            <div><p className="text-sm font-bold">Notificaciones</p><p className="mt-0.5 text-[11px] text-[var(--muted)]">{data.unread ? `${data.unread} sin leer` : "Todo al dia"}</p></div>
            {data.unread > 0 && <button className="icon-button" onClick={markAllRead} aria-label="Marcar todas como leidas" title="Marcar todas como leidas"><CheckCheck size={17} /></button>}
          </header>
          <div className="max-h-[28rem] overflow-y-auto">
            {loading ? <div className="grid h-32 place-items-center"><span className="loader" /></div> : error ? <p className="p-4 text-sm text-red-700">{error}</p> : data.items.length === 0 ? <p className="p-6 text-center text-sm text-[var(--muted)]">No tienes avisos pendientes.</p> : data.items.map((notification) => <NotificationItem key={notification.id} notification={notification} onOpen={openNotification} />)}
          </div>
          <footer className="border-t border-[var(--line)] p-2"><Link href="/notifications" onClick={() => setOpen(false)} className="flex h-9 items-center justify-center rounded-md text-xs font-bold text-[var(--accent)] hover:bg-slate-50">Ver todas</Link></footer>
        </section>
      )}
    </div>
  );
}

function NotificationItem({ notification, onOpen }: { notification: AppNotification; onOpen: (notification: AppNotification) => void }) {
  const Icon = notificationIcons[notification.type];
  return (
    <button className={`flex w-full gap-3 border-b border-[var(--line)] px-4 py-3 text-left last:border-b-0 hover:bg-slate-50 ${notification.read_at ? "opacity-70" : "bg-cyan-50/35"}`} onClick={() => void onOpen(notification)}>
      <span className={`mt-0.5 grid size-8 shrink-0 place-items-center rounded-md ${notification.type === "CRITICAL_INCIDENT" ? "bg-red-50 text-red-700" : "bg-slate-100 text-[var(--ink-soft)]"}`}><Icon size={16} /></span>
      <span className="min-w-0 flex-1"><strong className="block truncate text-xs text-[var(--ink)]">{notification.title}</strong><span className="mt-1 line-clamp-2 block text-xs leading-5 text-[var(--muted)]">{notification.body}</span><span className="mt-1 block text-[10px] font-semibold text-[var(--muted)]">{formatDate(notification.created_at, true)}</span></span>
      {!notification.read_at && <span className="mt-2 size-2 shrink-0 rounded-full bg-[var(--accent)]" />}
    </button>
  );
}
