import { Gauge, Wrench } from "lucide-react";

export default function MaintenancePage() {
  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] p-5">
      <section className="w-full max-w-md text-center">
        <div className="mx-auto grid size-12 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]">
          <Gauge size={26} />
        </div>
        <Wrench className="mx-auto mt-8 text-[var(--accent)]" size={34} />
        <h1 className="mt-4 text-2xl font-bold">Mantenimiento programado</h1>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          Estamos realizando una operacion tecnica controlada. ForgeOps volvera a estar disponible en breve.
        </p>
      </section>
    </main>
  );
}
