"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import { useEffect } from "react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <section className="panel mx-auto max-w-xl p-7 text-center">
      <AlertTriangle className="mx-auto text-[var(--warning)]" size={34} />
      <h2 className="mt-4 text-xl font-bold">No se pudo cargar esta vista</h2>
      <p className="mt-2 text-sm text-[var(--muted)]">
        Tus datos no se han modificado. Reintenta la operacion o facilita la referencia a soporte.
      </p>
      {error.digest && <p className="mt-3 font-mono text-[11px] text-[var(--muted)]">Ref. {error.digest}</p>}
      <button className="button-primary mx-auto mt-5" onClick={reset}>
        <RefreshCw size={17} /> Reintentar
      </button>
    </section>
  );
}
