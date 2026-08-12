"use client";

import { Boxes, BrainCircuit, Check, ClipboardList, FileText, PackageSearch, ShieldAlert, Wrench } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { moduleCatalog } from "@/lib/modules";
import type { CompanyModule } from "@/lib/types";

const moduleIcons = {
  PREVENTIVE: Wrench,
  INVENTORY: PackageSearch,
  DOCUMENTS: FileText,
  KNOWLEDGE: BrainCircuit,
};

const coreModules = [
  { title: "Activos", detail: "Estructura tecnica y estado de los equipos.", icon: Boxes },
  { title: "Incidencias", detail: "Registro y seguimiento de averias.", icon: ShieldAlert },
  { title: "Ordenes de trabajo", detail: "Planificacion y ejecucion de intervenciones.", icon: ClipboardList },
];

export default function ModulesPage() {
  const { user } = useAuth();
  const { company, updateModules, updateOnboarding } = useWorkspace();
  const [saving, setSaving] = useState<CompanyModule | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const canManage = user && ["SUPER_ADMIN", "ADMIN"].includes(user.role);

  if (!company) return <LoadingBlock />;

  async function toggleModule(module: CompanyModule, enabled: boolean) {
    if (!company || !canManage) return;
    setSaving(module);
    setError("");
    setSuccess("");
    const next = new Set(company.enabled_modules);
    if (enabled) next.add(module);
    else next.delete(module);
    if (module === "KNOWLEDGE" && enabled) next.add("DOCUMENTS");
    if (module === "DOCUMENTS" && !enabled) next.delete("KNOWLEDGE");
    try {
      await updateModules(Array.from(next));
      await updateOnboarding({ completed_step: "MODULES" });
      setSuccess("Configuracion modular actualizada");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron actualizar los modulos");
    } finally {
      setSaving(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Modulos de trabajo"
        description="Muestra a cada equipo solo las herramientas que necesita en su operacion diaria."
      />
      {error && <ErrorBanner message={error} />}
      {success && <div className="notice-success">{success}</div>}

      <section className="mb-7">
        <h3 className="text-sm font-bold">Nucleo operativo</h3>
        <p className="mt-1 text-xs text-[var(--muted)]">Estas funciones forman la trazabilidad basica y permanecen siempre activas.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {coreModules.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.title} className="flex items-start gap-3 border-y border-[var(--line)] py-4 md:border-y-0 md:border-l md:pl-4">
                <div className="grid size-9 shrink-0 place-items-center rounded-md bg-emerald-50 text-emerald-700"><Icon size={18} /></div>
                <div><p className="text-sm font-bold">{item.title}</p><p className="mt-1 text-xs leading-5 text-[var(--muted)]">{item.detail}</p></div>
                <Check className="ml-auto shrink-0 text-emerald-600" size={17} />
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel overflow-hidden">
        <header className="border-b border-[var(--line)] px-5 py-4">
          <h3 className="text-sm font-bold">Modulos opcionales</h3>
          <p className="mt-1 text-xs text-[var(--muted)]">Los cambios se aplican de inmediato a la navegacion y a la API de la empresa.</p>
        </header>
        <div className="divide-y divide-[var(--line)]">
          {(Object.keys(moduleCatalog) as CompanyModule[]).map((module) => {
            const definition = moduleCatalog[module];
            const Icon = moduleIcons[module];
            const enabled = company.enabled_modules.includes(module);
            const dependency = module === "KNOWLEDGE" ? "Requiere Documentacion tecnica" : null;
            return (
              <div key={module} className="flex flex-col gap-4 px-5 py-5 sm:flex-row sm:items-center">
                <div className={`grid size-10 shrink-0 place-items-center rounded-md ${enabled ? "bg-cyan-50 text-cyan-800" : "bg-[#edf0ef] text-[var(--muted)]"}`}><Icon size={19} /></div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-bold">{definition.title}</p>
                  <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{definition.description}</p>
                  {dependency && <p className="mt-1 text-[11px] font-semibold text-[var(--accent)]">{dependency}</p>}
                </div>
                <label className="inline-flex min-h-10 items-center gap-3 self-start sm:self-auto">
                  <span className="text-xs font-bold text-[var(--ink-soft)]">{enabled ? "Activo" : "Inactivo"}</span>
                  <input
                    className="module-toggle"
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) => void toggleModule(module, event.target.checked)}
                    disabled={!canManage || saving !== null}
                    aria-label={`${enabled ? "Desactivar" : "Activar"} ${definition.title}`}
                  />
                </label>
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
