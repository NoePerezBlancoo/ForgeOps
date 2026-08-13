"use client";

import {
  ArrowDown,
  ArrowUp,
  CalendarClock,
  ClipboardCheck,
  Pencil,
  Play,
  Plus,
  Search,
  Trash2,
  Wrench,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type {
  Asset,
  ChecklistTemplate,
  FrequencyType,
  PreventivePlan,
  Priority,
  UserOption,
} from "@/lib/types";

interface PlanForm {
  asset_id: string;
  assigned_to: string;
  checklist_template_id: string;
  name: string;
  description: string;
  frequency_type: FrequencyType;
  frequency_value: string;
  next_execution: string;
  estimated_duration: string;
  priority: Priority;
  active: boolean;
}

interface TemplateStepForm {
  title: string;
  instructions: string;
  required: boolean;
}

interface TemplateForm {
  name: string;
  description: string;
  active: boolean;
  items: TemplateStepForm[];
}

const emptyPlan: PlanForm = {
  asset_id: "",
  assigned_to: "",
  checklist_template_id: "",
  name: "",
  description: "",
  frequency_type: "MONTHS",
  frequency_value: "1",
  next_execution: "",
  estimated_duration: "60",
  priority: "MEDIUM",
  active: true,
};

const emptyTemplate: TemplateForm = {
  name: "",
  description: "",
  active: true,
  items: [{ title: "", instructions: "", required: true }],
};

function localDateTime(value: string): string {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export default function PreventiveMaintenancePage() {
  const { request, user } = useAuth();
  const { scopedPath } = useWorkspace();
  const [view, setView] = useState<"plans" | "checklists">("plans");
  const [plans, setPlans] = useState<PreventivePlan[]>([]);
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [planModal, setPlanModal] = useState(false);
  const [templateModal, setTemplateModal] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PreventivePlan | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<ChecklistTemplate | null>(null);
  const [planForm, setPlanForm] = useState<PlanForm>(emptyPlan);
  const [templateForm, setTemplateForm] = useState<TemplateForm>(emptyTemplate);
  const loadSequence = useRef(0);
  const canManage = Boolean(
    user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role),
  );

  const loadData = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setError("");
    try {
      const [planData, templateData, assetData, userData] = await Promise.all([
        request<PreventivePlan[]>(scopedPath("/preventive-maintenance")),
        request<ChecklistTemplate[]>("/preventive-maintenance/checklists/templates"),
        request<Asset[]>(scopedPath("/assets")),
        request<UserOption[]>("/users/options"),
      ]);
      if (sequence !== loadSequence.current) return;
      setPlans(planData);
      setTemplates(templateData);
      setAssets(assetData);
      setUsers(userData);
    } catch (requestError) {
      if (sequence !== loadSequence.current) return;
      setError(messageFor(requestError, "No se pudo cargar la planificacion preventiva"));
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [request, scopedPath]);

  useEffect(() => { void loadData(); }, [loadData]);

  const term = search.trim().toLowerCase();
  const filteredPlans = useMemo(() => plans.filter((plan) => !term || [
    plan.name,
    plan.asset.code,
    plan.asset.name,
    plan.assignee?.full_name,
    plan.checklist_template?.name,
  ].filter(Boolean).some((value) => value!.toLowerCase().includes(term))), [plans, term]);
  const filteredTemplates = useMemo(() => templates.filter((template) => !term || [
    template.name,
    template.description,
    ...template.items.map((item) => item.title),
  ].filter(Boolean).some((value) => value!.toLowerCase().includes(term))), [templates, term]);
  const dueCount = plans.filter((plan) => plan.active && new Date(plan.next_execution) <= new Date()).length;
  const activeTemplates = templates.filter((template) => template.active).length;

  function resetMessages() {
    setError("");
    setNotice("");
  }

  function openCreatePlan() {
    resetMessages();
    setEditingPlan(null);
    setPlanForm({
      ...emptyPlan,
      asset_id: assets[0]?.id ?? "",
      next_execution: localDateTime(new Date().toISOString()),
    });
    setPlanModal(true);
  }

  function openEditPlan(plan: PreventivePlan) {
    resetMessages();
    setEditingPlan(plan);
    setPlanForm({
      asset_id: plan.asset_id,
      assigned_to: plan.assigned_to ?? "",
      checklist_template_id: plan.checklist_template_id ?? "",
      name: plan.name,
      description: plan.description,
      frequency_type: plan.frequency_type,
      frequency_value: String(plan.frequency_value),
      next_execution: localDateTime(plan.next_execution),
      estimated_duration: String(plan.estimated_duration),
      priority: plan.priority,
      active: plan.active,
    });
    setPlanModal(true);
  }

  function openCreateTemplate() {
    resetMessages();
    setEditingTemplate(null);
    setTemplateForm(emptyTemplate);
    setTemplateModal(true);
  }

  function openEditTemplate(template: ChecklistTemplate) {
    resetMessages();
    setEditingTemplate(template);
    setTemplateForm({
      name: template.name,
      description: template.description ?? "",
      active: template.active,
      items: template.items.map((item) => ({
        title: item.title,
        instructions: item.instructions ?? "",
        required: item.required,
      })),
    });
    setTemplateModal(true);
  }

  async function savePlan(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        ...planForm,
        assigned_to: planForm.assigned_to || null,
        checklist_template_id: planForm.checklist_template_id || null,
        frequency_value: Number(planForm.frequency_value),
        estimated_duration: Number(planForm.estimated_duration),
        next_execution: new Date(planForm.next_execution).toISOString(),
      };
      if (editingPlan) delete (payload as Partial<typeof payload>).asset_id;
      await request(
        editingPlan ? `/preventive-maintenance/${editingPlan.id}` : "/preventive-maintenance",
        { method: editingPlan ? "PATCH" : "POST", body: JSON.stringify(payload) },
      );
      setPlanModal(false);
      setNotice(editingPlan ? "Plan preventivo actualizado" : "Plan preventivo creado");
      await loadData();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo guardar el plan"));
    } finally {
      setSaving(false);
    }
  }

  async function saveTemplate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload = {
        name: templateForm.name,
        description: templateForm.description || null,
        active: templateForm.active,
        items: templateForm.items.map((item, index) => ({
          ...item,
          instructions: item.instructions || null,
          position: index + 1,
        })),
      };
      await request(
        editingTemplate
          ? `/preventive-maintenance/checklists/templates/${editingTemplate.id}`
          : "/preventive-maintenance/checklists/templates",
        { method: editingTemplate ? "PATCH" : "POST", body: JSON.stringify(payload) },
      );
      setTemplateModal(false);
      setNotice(editingTemplate ? "Checklist actualizado" : "Checklist creado");
      await loadData();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo guardar el checklist"));
    } finally {
      setSaving(false);
    }
  }

  async function generateOne(plan: PreventivePlan) {
    setGenerating(plan.id);
    resetMessages();
    try {
      await request(`/preventive-maintenance/${plan.id}/generate-work-order`, { method: "POST" });
      setNotice(`Orden preventiva generada para ${plan.asset.code}`);
      await loadData();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo generar la orden"));
    } finally {
      setGenerating("");
    }
  }

  async function generateDue() {
    setGenerating("all");
    resetMessages();
    try {
      const result = await request<{ generated: number; skipped: number }>(
        "/preventive-maintenance/actions/generate-due",
        { method: "POST" },
      );
      setNotice(`${result.generated} ordenes generadas, ${result.skipped} omitidas`);
      await loadData();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudieron generar las ordenes"));
    } finally {
      setGenerating("");
    }
  }

  function changeStep(index: number, changes: Partial<TemplateStepForm>) {
    setTemplateForm((current) => ({
      ...current,
      items: current.items.map((item, itemIndex) => itemIndex === index ? { ...item, ...changes } : item),
    }));
  }

  function moveStep(index: number, direction: -1 | 1) {
    setTemplateForm((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.items.length) return current;
      const items = [...current.items];
      [items[index], items[target]] = [items[target], items[index]];
      return { ...current, items };
    });
  }

  function removeStep(index: number) {
    setTemplateForm((current) => current.items.length === 1
      ? current
      : { ...current, items: current.items.filter((_, itemIndex) => itemIndex !== index) });
  }

  return (
    <>
      <PageHeader
        title="Mantenimiento preventivo"
        description="Planificacion recurrente, procedimientos y ordenes listas para ejecutar."
        actions={canManage ? view === "plans" ? <>
          <button className="button-secondary" onClick={generateDue} disabled={generating === "all"}><Play size={16} /> Generar vencidos ({dueCount})</button>
          <button className="button-primary" onClick={openCreatePlan}><Plus size={17} /> Nuevo plan</button>
        </> : <button className="button-primary" onClick={openCreateTemplate}><Plus size={17} /> Nuevo checklist</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}

      <section className="mb-4 grid gap-3 sm:grid-cols-3">
        <Metric value={plans.filter((plan) => plan.active).length} label="Planes activos" icon={CalendarClock} />
        <Metric value={dueCount} label="Planes vencidos" icon={Wrench} alert={dueCount > 0} />
        <Metric value={activeTemplates} label="Checklists disponibles" icon={ClipboardCheck} />
      </section>

      <section className="panel mb-4 p-3">
        <div className="grid gap-3 md:grid-cols-[auto_minmax(220px,1fr)] md:items-center">
          <div className="inline-flex self-start rounded-md border border-[var(--line)] bg-slate-50 p-1">
            <button className={`h-8 rounded px-3 text-xs font-bold ${view === "plans" ? "bg-white shadow-sm" : "text-[var(--muted)]"}`} onClick={() => setView("plans")}>Planes</button>
            <button className={`h-8 rounded px-3 text-xs font-bold ${view === "checklists" ? "bg-white shadow-sm" : "text-[var(--muted)]"}`} onClick={() => setView("checklists")}>Checklists</button>
          </div>
          <label className="relative min-w-0"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={view === "plans" ? "Buscar plan, activo, responsable o checklist" : "Buscar checklist o paso"} /></label>
        </div>
      </section>

      {loading ? <LoadingBlock /> : view === "plans" ? (
        <PlanTable plans={filteredPlans} canManage={canManage} generating={generating} onGenerate={generateOne} onEdit={openEditPlan} />
      ) : (
        <TemplateTable templates={filteredTemplates} plans={plans} canManage={canManage} onEdit={openEditTemplate} />
      )}

      <Modal open={planModal} title={editingPlan ? "Editar plan preventivo" : "Nuevo plan preventivo"} description="Periodicidad, procedimiento y responsable de la intervencion." onClose={() => setPlanModal(false)}>
        <form onSubmit={savePlan}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            {error && <div className="sm:col-span-2"><ErrorBanner message={error} /></div>}
            <Field label="Activo"><select className="field" value={planForm.asset_id} onChange={(event) => setPlanForm({ ...planForm, asset_id: event.target.value })} disabled={Boolean(editingPlan)} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} - {asset.name}</option>)}</select></Field>
            <Field label="Responsable"><select className="field" value={planForm.assigned_to} onChange={(event) => setPlanForm({ ...planForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}</select></Field>
            <div className="sm:col-span-2"><Field label="Nombre"><input className="field" value={planForm.name} onChange={(event) => setPlanForm({ ...planForm, name: event.target.value })} minLength={4} maxLength={180} required /></Field></div>
            <Field label="Checklist"><select className="field" value={planForm.checklist_template_id} onChange={(event) => setPlanForm({ ...planForm, checklist_template_id: event.target.value })}><option value="">Sin checklist</option>{templates.filter((template) => template.active || template.id === editingPlan?.checklist_template_id).map((template) => <option key={template.id} value={template.id}>{template.name} ({template.items.length})</option>)}</select></Field>
            <Field label="Prioridad"><select className="field" value={planForm.priority} onChange={(event) => setPlanForm({ ...planForm, priority: event.target.value as Priority })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Frecuencia"><select className="field" value={planForm.frequency_type} onChange={(event) => setPlanForm({ ...planForm, frequency_type: event.target.value as FrequencyType })}><option value="DAYS">Dias</option><option value="WEEKS">Semanas</option><option value="MONTHS">Meses</option><option value="YEARS">Anos</option></select></Field>
            <Field label="Cada"><input className="field" type="number" min="1" max="365" value={planForm.frequency_value} onChange={(event) => setPlanForm({ ...planForm, frequency_value: event.target.value })} required /></Field>
            <Field label="Proxima ejecucion"><input className="field" type="datetime-local" value={planForm.next_execution} onChange={(event) => setPlanForm({ ...planForm, next_execution: event.target.value })} required /></Field>
            <Field label="Duracion estimada (min)"><input className="field" type="number" min="1" max="10080" value={planForm.estimated_duration} onChange={(event) => setPlanForm({ ...planForm, estimated_duration: event.target.value })} required /></Field>
            <Field label="Estado"><select className="field" value={planForm.active ? "active" : "inactive"} onChange={(event) => setPlanForm({ ...planForm, active: event.target.value === "active" })}><option value="active">Activo</option><option value="inactive">Inactivo</option></select></Field>
            <div className="sm:col-span-2"><Field label="Trabajo previsto"><textarea className="field min-h-24" value={planForm.description} onChange={(event) => setPlanForm({ ...planForm, description: event.target.value })} minLength={10} maxLength={5000} required /></Field></div>
          </div>
          <ModalFooter saving={saving} onCancel={() => setPlanModal(false)} label="Guardar plan" />
        </form>
      </Modal>

      <Modal open={templateModal} title={editingTemplate ? "Editar checklist" : "Nuevo checklist"} description="Procedimiento reutilizable que se copiara en cada orden preventiva." onClose={() => setTemplateModal(false)}>
        <form onSubmit={saveTemplate}>
          <div className="space-y-5 p-5 sm:p-6">
            {error && <ErrorBanner message={error} />}
            <div className="grid gap-4 sm:grid-cols-[1fr_150px]"><Field label="Nombre"><input className="field" value={templateForm.name} onChange={(event) => setTemplateForm({ ...templateForm, name: event.target.value })} required maxLength={180} /></Field><Field label="Estado"><select className="field" value={templateForm.active ? "active" : "inactive"} onChange={(event) => setTemplateForm({ ...templateForm, active: event.target.value === "active" })}><option value="active">Activo</option><option value="inactive">Inactivo</option></select></Field></div>
            <Field label="Descripcion"><textarea className="field" value={templateForm.description} onChange={(event) => setTemplateForm({ ...templateForm, description: event.target.value })} maxLength={4000} /></Field>
            <div>
              <div className="mb-3 flex items-center justify-between"><div><p className="field-label">Pasos</p><p className="mt-1 text-xs text-[var(--muted)]">El orden se conservara en la orden de trabajo.</p></div><button type="button" className="button-secondary" onClick={() => setTemplateForm((current) => ({ ...current, items: [...current.items, { title: "", instructions: "", required: true }] }))}><Plus size={15} /> Anadir paso</button></div>
              <div className="space-y-3">{templateForm.items.map((item, index) => <div key={index} className="rounded-md border border-[var(--line)] bg-slate-50 p-3"><div className="flex items-start gap-3"><span className="grid size-7 shrink-0 place-items-center rounded-md bg-[var(--ink)] text-xs font-bold text-white">{index + 1}</span><div className="min-w-0 flex-1 space-y-3"><input className="field bg-white" value={item.title} onChange={(event) => changeStep(index, { title: event.target.value })} placeholder="Comprobacion" required maxLength={500} /><textarea className="field bg-white" value={item.instructions} onChange={(event) => changeStep(index, { instructions: event.target.value })} placeholder="Instrucciones opcionales" maxLength={4000} /><label className="flex items-center gap-2 text-xs font-semibold"><input type="checkbox" checked={item.required} onChange={(event) => changeStep(index, { required: event.target.checked })} /> Obligatorio para finalizar</label></div><div className="flex shrink-0 flex-col gap-1"><button type="button" className="icon-button size-8" onClick={() => moveStep(index, -1)} disabled={index === 0} aria-label="Subir paso" title="Subir"><ArrowUp size={14} /></button><button type="button" className="icon-button size-8" onClick={() => moveStep(index, 1)} disabled={index === templateForm.items.length - 1} aria-label="Bajar paso" title="Bajar"><ArrowDown size={14} /></button><button type="button" className="icon-button size-8 text-red-700" onClick={() => removeStep(index)} disabled={templateForm.items.length === 1} aria-label="Eliminar paso" title="Eliminar"><Trash2 size={14} /></button></div></div></div>)}</div>
            </div>
          </div>
          <ModalFooter saving={saving} onCancel={() => setTemplateModal(false)} label="Guardar checklist" />
        </form>
      </Modal>
    </>
  );
}

function PlanTable({ plans, canManage, generating, onGenerate, onEdit }: { plans: PreventivePlan[]; canManage: boolean; generating: string; onGenerate: (plan: PreventivePlan) => void; onEdit: (plan: PreventivePlan) => void }) {
  return <section className="panel overflow-hidden">{plans.length === 0 ? <EmptyState title="No hay planes preventivos" detail="Registra el primer plan para un activo." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Plan</th><th>Activo</th><th>Frecuencia</th><th>Proxima ejecucion</th><th>Responsable</th><th>Procedimiento</th><th>Prioridad</th><th className="w-24">Acciones</th></tr></thead><tbody>{plans.map((plan) => { const overdue = plan.active && new Date(plan.next_execution) <= new Date(); return <tr key={plan.id}><td><p className="font-bold text-[var(--ink)]">{plan.name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{plan.active ? "Activo" : "Inactivo"}</p></td><td><p className="font-semibold">{plan.asset.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{plan.asset.name}</p></td><td>{frequencyLabel(plan.frequency_type, plan.frequency_value)}</td><td><span className={overdue ? "font-bold text-red-700" : ""}>{formatDate(plan.next_execution, true)}</span></td><td>{plan.assignee?.full_name ?? "Sin asignar"}</td><td>{plan.checklist_template ? <span className="inline-flex items-center gap-1.5 text-xs font-semibold"><ClipboardCheck size={14} /> {plan.checklist_template.name}</span> : <span className="text-xs text-[var(--muted)]">Sin checklist</span>}</td><td><StatusBadge value={plan.priority} /></td><td>{canManage && <div className="flex gap-2"><button className="icon-button" onClick={() => void onGenerate(plan)} disabled={Boolean(generating)} title="Generar orden" aria-label={`Generar orden para ${plan.name}`}><Wrench size={16} /></button><button className="icon-button" onClick={() => onEdit(plan)} title="Editar plan" aria-label={`Editar ${plan.name}`}><Pencil size={16} /></button></div>}</td></tr>; })}</tbody></table></div>}</section>;
}

function TemplateTable({ templates, plans, canManage, onEdit }: { templates: ChecklistTemplate[]; plans: PreventivePlan[]; canManage: boolean; onEdit: (template: ChecklistTemplate) => void }) {
  return <section className="panel overflow-hidden">{templates.length === 0 ? <EmptyState title="No hay checklists" detail="Crea un procedimiento reutilizable para tus planes preventivos." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Checklist</th><th>Pasos</th><th>Uso</th><th>Actualizado</th><th>Estado</th><th className="w-16">Acciones</th></tr></thead><tbody>{templates.map((template) => <tr key={template.id}><td><p className="font-bold text-[var(--ink)]">{template.name}</p><p className="mt-1 max-w-xl text-[11px] text-[var(--muted)]">{template.description ?? template.items[0]?.title}</p></td><td><span className="font-bold">{template.items.length}</span> <span className="text-xs text-[var(--muted)]">comprobaciones</span></td><td>{plans.filter((plan) => plan.checklist_template_id === template.id).length} planes</td><td>{formatDate(template.updated_at, true)}</td><td><StatusBadge value={template.active ? "ACTIVE" : "OUT_OF_SERVICE"} /></td><td>{canManage && <button className="icon-button" onClick={() => onEdit(template)} title="Editar checklist" aria-label={`Editar ${template.name}`}><Pencil size={16} /></button>}</td></tr>)}</tbody></table></div>}</section>;
}

function Metric({ value, label, icon: Icon, alert = false }: { value: number; label: string; icon: typeof Wrench; alert?: boolean }) {
  return <article className="panel flex items-center gap-3 p-4"><div className={`grid size-9 place-items-center rounded-md ${alert ? "bg-red-50 text-red-700" : "bg-cyan-50 text-cyan-800"}`}><Icon size={18} /></div><div><p className="text-xl font-bold">{value}</p><p className="text-[11px] font-semibold text-[var(--muted)]">{label}</p></div></article>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function ModalFooter({ saving, onCancel, label }: { saving: boolean; onCancel: () => void; label: string }) {
  return <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={onCancel}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : label}</button></footer>;
}

function frequencyLabel(type: FrequencyType, value: number): string {
  const singular: Record<FrequencyType, string> = { DAYS: "dia", WEEKS: "semana", MONTHS: "mes", YEARS: "ano" };
  return `Cada ${value} ${value === 1 ? singular[type] : labelFor(type).toLowerCase()}`;
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}
