import { CloudOff, Gauge, RefreshCw } from "lucide-react";

export default function OfflinePage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] p-5">
      <section className="w-full max-w-md text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]">
          <Gauge size={26} />
        </div>
        <CloudOff className="mx-auto mt-8 text-[var(--muted)]" size={34} />
        <h1 className="mt-4 text-2xl font-bold">ForgeOps sin conexion</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          No podemos abrir esta vista ahora. Los borradores compatibles permanecen guardados en este dispositivo.
        </p>
        <a href="/dashboard" className="button-primary mt-6 h-11 justify-center">
          <RefreshCw size={17} /> Reintentar
        </a>
      </section>
    </main>
  );
}
