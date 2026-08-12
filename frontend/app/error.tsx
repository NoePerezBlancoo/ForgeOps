"use client";

import { AlertTriangle, Home, RefreshCw } from "lucide-react";
import { useEffect } from "react";

export default function ApplicationError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("ForgeOps UI error", { digest: error.digest });
  }, [error]);

  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] px-5 py-10">
      <section className="w-full max-w-md rounded-md border border-[var(--line)] bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-5 grid size-11 place-items-center rounded-md bg-red-50 text-red-700">
          <AlertTriangle size={22} />
        </div>
        <h1 className="text-xl font-bold text-[var(--ink)]">No se pudo cargar esta vista</h1>
        <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
          La operacion no se ha completado. Puedes volver a intentarlo o regresar al panel.
        </p>
        {error.digest && (
          <p className="mt-4 rounded-md bg-[var(--canvas)] px-3 py-2 font-mono text-xs text-[var(--muted)]">
            Referencia: {error.digest}
          </p>
        )}
        <div className="mt-6 flex flex-col gap-2 sm:flex-row">
          <button className="button-primary justify-center" onClick={reset}>
            <RefreshCw size={16} /> Reintentar
          </button>
          <a className="button-secondary justify-center" href="/dashboard">
            <Home size={16} /> Ir al panel
          </a>
        </div>
      </section>
    </main>
  );
}
