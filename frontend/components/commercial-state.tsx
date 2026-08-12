"use client";

import { ArrowRight, CalendarClock, LockKeyhole, Settings2 } from "lucide-react";
import Link from "next/link";

import { moduleCatalog } from "@/lib/modules";
import type { Company, CompanyModule, UserRole } from "@/lib/types";

export function TrialBanner({ company }: { company: Company }) {
  if (company.access_status !== "TRIAL") return null;
  const days = company.trial_days_remaining ?? 0;
  return (
    <div className={`flex min-h-10 items-center gap-2 border-b px-4 text-xs font-semibold md:px-6 lg:px-8 ${days <= 5 ? "border-amber-200 bg-amber-50 text-amber-900" : "border-cyan-100 bg-cyan-50 text-cyan-950"}`}>
      <CalendarClock size={15} />
      <span>Prueba profesional: {days} {days === 1 ? "dia disponible" : "dias disponibles"}</span>
      <Link href="/getting-started" className="ml-auto inline-flex items-center gap-1 font-bold">
        Completar puesta en marcha <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export function AccessBlocked({ company }: { company: Company }) {
  const salesEmail = process.env.NEXT_PUBLIC_SALES_EMAIL ?? "contacto@forgeops.local";
  const suspended = company.access_status === "SUSPENDED";
  return (
    <section className="mx-auto max-w-2xl py-12 text-center">
      <div className="mx-auto grid size-12 place-items-center rounded-md bg-red-50 text-red-700">
        <LockKeyhole size={23} />
      </div>
      <h2 className="mt-5 text-2xl font-bold">{suspended ? "Cuenta temporalmente suspendida" : "La prueba de 30 dias ha finalizado"}</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[var(--muted)]">
        Los datos de {company.name} se conservan. Activa la continuidad del servicio para recuperar la operacion completa del equipo.
      </p>
      <div className="mt-7 flex flex-wrap justify-center gap-2">
        <a className="button-primary" href={`mailto:${salesEmail}?subject=Continuidad ForgeOps - ${encodeURIComponent(company.name)}`}>
          Solicitar continuidad <ArrowRight size={16} />
        </a>
        <Link className="button-secondary" href="/settings">Revisar mi cuenta</Link>
      </div>
    </section>
  );
}

export function ModuleUnavailable({ module, role }: { module: CompanyModule; role?: UserRole }) {
  const definition = moduleCatalog[module];
  const isAdmin = role === "ADMIN" || role === "SUPER_ADMIN";
  return (
    <section className="mx-auto max-w-2xl py-12 text-center">
      <div className="mx-auto grid size-12 place-items-center rounded-md bg-cyan-50 text-cyan-800">
        <Settings2 size={23} />
      </div>
      <h2 className="mt-5 text-2xl font-bold">{definition.title} no esta activo</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[var(--muted)]">{definition.description}</p>
      <div className="mt-7 flex justify-center gap-2">
        {isAdmin && <Link className="button-primary" href="/modules">Configurar modulos</Link>}
        <Link className="button-secondary" href="/dashboard">Volver al dashboard</Link>
      </div>
    </section>
  );
}
