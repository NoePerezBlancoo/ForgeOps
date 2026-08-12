"use client";

import { ArrowRight, Check, Circle, CircleHelp, X } from "lucide-react";
import Link from "next/link";

import { useWorkspace } from "@/components/workspace-provider";

export function HelpDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { onboarding } = useWorkspace();
  if (!open) return null;
  const nextSteps = onboarding?.steps.filter((step) => !step.complete).slice(0, 4) ?? [];

  return (
    <div className="fixed inset-0 z-60">
      <button className="absolute inset-0 bg-black/35" onClick={onClose} aria-label="Cerrar ayuda" />
      <aside className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col border-l border-[var(--line)] bg-white shadow-2xl" aria-label="Ayuda de ForgeOps">
        <header className="flex items-center gap-3 border-b border-[var(--line)] px-5 py-4">
          <div className="grid size-9 place-items-center rounded-md bg-cyan-50 text-cyan-800"><CircleHelp size={19} /></div>
          <div>
            <h2 className="text-sm font-bold">Ayuda y primeros pasos</h2>
            <p className="mt-0.5 text-xs text-[var(--muted)]">Siguiente accion recomendada para tu empresa</p>
          </div>
          <button className="icon-button ml-auto" onClick={onClose} aria-label="Cerrar panel de ayuda"><X size={18} /></button>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {onboarding && (
            <section>
              <div className="flex items-end justify-between">
                <div><p className="text-xs font-bold uppercase text-[var(--muted)]">Configuracion</p><p className="mt-1 text-sm font-bold">{onboarding.completed} de {onboarding.total} pasos</p></div>
                <strong className="text-sm text-[var(--accent)]">{onboarding.percent}%</strong>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#e8ecea]"><div className="h-full bg-[var(--accent)]" style={{ width: `${onboarding.percent}%` }} /></div>
            </section>
          )}

          <section className="mt-7">
            <h3 className="text-sm font-bold">Continua por aqui</h3>
            <div className="mt-3 divide-y divide-[var(--line)] border-y border-[var(--line)]">
              {nextSteps.map((step) => (
                <Link key={step.key} href={step.href} onClick={onClose} className="flex gap-3 py-4">
                  <Circle className="mt-0.5 shrink-0 text-[var(--accent)]" size={17} />
                  <span className="min-w-0 flex-1"><strong className="block text-xs">{step.title}</strong><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{step.description}</span></span>
                  <ArrowRight className="mt-0.5 shrink-0 text-[var(--muted)]" size={16} />
                </Link>
              ))}
              {nextSteps.length === 0 && <div className="flex items-center gap-3 py-4 text-sm font-semibold text-emerald-700"><Check size={18} /> Puesta en marcha completada</div>}
            </div>
          </section>

          <section className="mt-7">
            <h3 className="text-sm font-bold">Flujo diario recomendado</h3>
            <ol className="mt-3 space-y-3 text-xs leading-5 text-[var(--ink-soft)]">
              <li><strong>1. Registra</strong> la incidencia sobre el activo afectado.</li>
              <li><strong>2. Convierte</strong> el trabajo necesario en una orden asignable.</li>
              <li><strong>3. Ejecuta</strong> la intervencion y documenta tiempos, causa y solucion.</li>
              <li><strong>4. Previene</strong> recurrencias con planes y documentacion tecnica.</li>
            </ol>
          </section>
        </div>

        <footer className="border-t border-[var(--line)] p-4">
          <Link href="/getting-started" onClick={onClose} className="button-primary w-full justify-center">Abrir tutorial completo <ArrowRight size={16} /></Link>
        </footer>
      </aside>
    </div>
  );
}
