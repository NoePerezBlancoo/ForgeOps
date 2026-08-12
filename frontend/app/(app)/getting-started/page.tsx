"use client";

import { ArrowRight, BookOpen, Check, CheckCircle2, Circle, ClipboardList, FileText, ShieldAlert, Wrench } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";

const guide = [
  {
    number: "01",
    title: "Detecta y registra",
    description: "Selecciona el activo, describe el sintoma y marca prioridad y minutos de parada. La incidencia es el origen de la trazabilidad correctiva.",
    action: "Registrar incidencia",
    href: "/incidents?new=1",
    icon: ShieldAlert,
  },
  {
    number: "02",
    title: "Planifica el trabajo",
    description: "Crea una orden, asigna responsable y fecha, y estima la duracion. El equipo comparte una unica cola de trabajo priorizada.",
    action: "Ver ordenes",
    href: "/work-orders",
    icon: ClipboardList,
  },
  {
    number: "03",
    title: "Ejecuta y cierra",
    description: "Actualiza el estado durante la intervencion y documenta tiempo real, causa raiz, resolucion y observaciones para futuras averias.",
    action: "Abrir trabajo",
    href: "/work-orders",
    icon: Wrench,
  },
  {
    number: "04",
    title: "Estandariza y previene",
    description: "Convierte la experiencia en planes preventivos y adjunta procedimientos o manuales al activo para que el conocimiento quede disponible.",
    action: "Abrir documentos",
    href: "/documents",
    icon: FileText,
  },
];

export default function GettingStartedPage() {
  const { onboarding, updateOnboarding } = useWorkspace();
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  if (!onboarding) return <LoadingBlock />;
  const next = onboarding.steps.find((step) => !step.complete);

  async function confirmWelcome() {
    setSaving(true);
    setError("");
    try {
      await updateOnboarding({ completed_step: "WELCOME" });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar el progreso");
    } finally {
      setSaving(false);
    }
  }

  async function completeGuide() {
    setSaving(true);
    setError("");
    try {
      await updateOnboarding({ tour_completed: true });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo completar la guia");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Primeros pasos"
        description="Configura ForgeOps siguiendo un recorrido breve y empieza a trabajar con un flujo de mantenimiento real."
        actions={next ? (
          next.key === "WELCOME" ? (
            <button className="button-primary" onClick={() => void confirmWelcome()} disabled={saving}>Empezar recorrido <ArrowRight size={16} /></button>
          ) : (
            <Link className="button-primary" href={next.href}>Siguiente paso <ArrowRight size={16} /></Link>
          )
        ) : undefined}
      />
      {error && <ErrorBanner message={error} />}

      <section className="panel overflow-hidden">
        <div className="grid gap-5 p-5 lg:grid-cols-[0.38fr_0.62fr] lg:p-6">
          <div>
            <p className="text-xs font-bold uppercase text-[var(--accent)]">Puesta en marcha</p>
            <p className="mt-3 text-3xl font-bold">{onboarding.percent}%</p>
            <p className="mt-2 text-sm text-[var(--muted)]">{onboarding.completed} de {onboarding.total} pasos completados</p>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-[#e8ecea]"><div className="h-full bg-[var(--accent)]" style={{ width: `${onboarding.percent}%` }} /></div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {onboarding.steps.map((step) => (
              <Link key={step.key} href={step.href} className={`flex min-h-24 gap-3 border p-4 ${step.complete ? "border-emerald-200 bg-emerald-50/45" : "border-[var(--line)] bg-white"}`}>
                {step.complete ? <CheckCircle2 className="mt-0.5 shrink-0 text-emerald-700" size={18} /> : <Circle className="mt-0.5 shrink-0 text-[var(--muted)]" size={18} />}
                <span><strong className="block text-xs">{step.title}</strong><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">{step.description}</span></span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section id="guide" className="mt-8 scroll-mt-28">
        <div className="mb-4 flex items-end justify-between gap-4">
          <div><h3 className="text-lg font-bold">Guia operativa</h3><p className="mt-1 text-sm text-[var(--muted)]">El ciclo diario de mantenimiento en cuatro decisiones claras.</p></div>
          <BookOpen className="hidden text-[var(--muted)] sm:block" size={24} />
        </div>
        <div className="border-y border-[var(--line)]">
          {guide.map((item) => {
            const Icon = item.icon;
            return (
              <article key={item.number} className="grid gap-4 border-b border-[var(--line)] py-6 last:border-b-0 md:grid-cols-[64px_180px_1fr_auto] md:items-center">
                <span className="text-sm font-bold text-[var(--accent)]">{item.number}</span>
                <div className="flex items-center gap-3"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Icon size={18} /></div><h4 className="text-sm font-bold">{item.title}</h4></div>
                <p className="text-sm leading-6 text-[var(--muted)]">{item.description}</p>
                <Link href={item.href} className="button-secondary justify-center">{item.action} <ArrowRight size={15} /></Link>
              </article>
            );
          })}
        </div>
        {!onboarding.tour_completed && (
          <div className="mt-5 flex justify-end"><button className="button-primary" onClick={() => void completeGuide()} disabled={saving}><Check size={16} /> Marcar guia como revisada</button></div>
        )}
      </section>
    </>
  );
}
