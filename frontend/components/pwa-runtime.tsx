"use client";

import { CloudOff, Download, RefreshCw, Wifi } from "lucide-react";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { listOfflineOperations } from "@/lib/offline-queue";

interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export function PwaRuntime() {
  const pathname = usePathname();
  const [online, setOnline] = useState(true);
  const [pending, setPending] = useState(0);
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);

  const refreshQueue = useCallback(async () => {
    if (!("indexedDB" in window)) return;
    const operations = await listOfflineOperations();
    setPending(operations.filter((operation) => operation.status !== "SYNCING").length);
  }, []);

  useEffect(() => {
    setOnline(navigator.onLine);
    const onOnline = () => setOnline(true);
    const onOffline = () => setOnline(false);
    const onInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    window.addEventListener("beforeinstallprompt", onInstall);
    window.addEventListener("forgeops:queue-change", refreshQueue);
    void refreshQueue();
    if ("serviceWorker" in navigator && process.env.NEXT_PUBLIC_PWA_ENABLED !== "false") {
      void navigator.serviceWorker.register("/sw.js", { scope: "/" });
    }
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
      window.removeEventListener("beforeinstallprompt", onInstall);
      window.removeEventListener("forgeops:queue-change", refreshQueue);
    };
  }, [refreshQueue]);

  if (pathname.startsWith("/control")) return null;
  if (online && pending === 0 && !installPrompt) return null;

  async function install() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  return (
    <div className="connectivity-bar" role="status">
      <span className="flex min-w-0 items-center gap-2">
        {online ? <Wifi size={15} /> : <CloudOff size={15} />}
        <span className="truncate">
          {online ? `${pending} cambios locales pendientes` : "Sin conexion. Los borradores se guardan en este dispositivo."}
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        {online && pending > 0 && <RefreshCw size={14} aria-label="Sincronizacion pendiente" />}
        {installPrompt && (
          <button onClick={() => void install()} className="connectivity-action">
            <Download size={14} /> Instalar
          </button>
        )}
      </span>
    </div>
  );
}
