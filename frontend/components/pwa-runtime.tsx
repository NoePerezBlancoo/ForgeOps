"use client";

import { AlertTriangle, CloudOff, Download, RefreshCw, Wifi } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import {
  listOfflineOperations,
  removeOfflineOperation,
  updateOfflineOperation,
  type OfflineOperation,
  type OfflineOwner,
} from "@/lib/offline-queue";
import { OfflineSyncEngine } from "@/lib/offline-sync";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function PwaRuntime() {
  const { request, user } = useAuth();
  const pathname = usePathname();
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState(0);
  const [failed, setFailed] = useState(0);
  const [conflicts, setConflicts] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const owner = useMemo<OfflineOwner | null>(
    () => user ? { companyId: user.company_id, userId: user.id } : null,
    [user],
  );

  const refreshQueue = useCallback(async () => {
    if (!("indexedDB" in window) || !owner) {
      setPending(0);
      setFailed(0);
      setConflicts(0);
      return;
    }
    try {
      const operations = await listOfflineOperations(owner);
      setPending(operations.filter((operation) => operation.status === "PENDING").length);
      setFailed(operations.filter((operation) => operation.status === "FAILED").length);
      setConflicts(operations.filter((operation) => operation.status === "CONFLICT").length);
    } catch {
      setPending(0);
      setFailed(0);
      setConflicts(0);
    }
  }, [owner]);

  const engine = useMemo(() => owner ? new OfflineSyncEngine<OfflineOperation>({
    list: () => listOfflineOperations(owner),
    update: updateOfflineOperation,
    remove: removeOfflineOperation,
    send: async (operation) => {
      await request<unknown>(operation.path, {
        method: "POST",
        body: JSON.stringify(operation.payload),
      });
    },
    classifyFailure: (error) => error instanceof ApiError
      ? { kind: "http", status: error.status, message: error.message }
      : { kind: "network", message: "Conexion interrumpida durante el envio" },
  }) : null, [owner, request]);

  const synchronize = useCallback(async () => {
    if (!engine || !navigator.onLine) return;
    setSyncing(true);
    try {
      await engine.run();
    } catch {
      return;
    } finally {
      await refreshQueue();
      setSyncing(false);
    }
  }, [engine, refreshQueue]);

  useEffect(() => {
    setOnline(navigator.onLine);
    const onOnline = () => {
      setOnline(true);
      window.dispatchEvent(new Event("forgeops:sync-request"));
    };
    const onOffline = () => setOnline(false);
    const onInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("beforeinstallprompt", onInstall);
    window.addEventListener("forgeops:queue-change", refreshQueue);
    window.addEventListener("forgeops:sync-request", synchronize);
    void refreshQueue();
    if ("serviceWorker" in navigator && process.env.NEXT_PUBLIC_PWA_ENABLED !== "false") {
      void navigator.serviceWorker.register("/sw.js", { scope: "/" });
    }
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("beforeinstallprompt", onInstall);
      window.removeEventListener("forgeops:queue-change", refreshQueue);
      window.removeEventListener("forgeops:sync-request", synchronize);
    };
  }, [refreshQueue, synchronize]);

  useEffect(() => {
    if (online && owner) void synchronize();
  }, [online, owner, synchronize]);

  if (pathname.startsWith("/control")) return null;
  if (online && pending === 0 && failed === 0 && conflicts === 0 && !installPrompt) return null;

  async function install() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  return (
    <div className="connectivity-bar" role="status">
      <span className="flex min-w-0 items-center gap-2">
        {conflicts > 0 ? <AlertTriangle size={15} /> : online ? <Wifi size={15} /> : <CloudOff size={15} />}
        <span className="truncate">
          {conflicts > 0
            ? `${conflicts} cambios requieren revision`
            : online
              ? `${pending + failed} cambios locales pendientes`
              : "Sin conexion. Los cambios compatibles se guardan en este dispositivo."}
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        {user && pending + failed + conflicts > 0 && <Link href="/sync" className="connectivity-action">Ver cola</Link>}
        {online && pending + failed > 0 && (
          <button onClick={() => void synchronize()} className="connectivity-action" disabled={syncing} aria-label="Sincronizar cambios">
            <RefreshCw className={syncing ? "animate-spin" : ""} size={14} />
          </button>
        )}
        {installPrompt && (
          <button onClick={() => void install()} className="connectivity-action">
            <Download size={14} /> Instalar
          </button>
        )}
      </span>
    </div>
  );
}
