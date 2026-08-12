"use client";

import { CalendarClock, Pencil, Play, Plus, Search, Wrench } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type {
  Asset,
  FrequencyType,
  PreventivePlan,
  Priority,
  UserOption,
} from "@/lib/types";

interface PlanForm {
  asset_id: string;
  assigned_to: string;
  name: string;
  description: string;
  frequency_type: FrequencyType;
  frequency_value: string;
  next_execution: string;
  estimated_duration: string;
  priority: Priority;
  active: boolean;
}

const emptyForm: PlanForm = {
  asset_id: "",
  assigned_to: "",
  name: "",
  description: "",
  frequency_type: "MONTHS",
  frequency_value: "1",
  next_execution: "",
  estimated_duration: "60",
  priority: "MEDIUM",
  active: true,
};

function localDateTime(value: string): string {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export default function PreventiveMaintenancePage() {
  const { request, user } = useAuth();
  const [plans, setPlans] = useState<PreventivePlan[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<PreventivePlan | null>(null);
  const [form, setForm] = useState<PlanForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState("");
  const canManage = Boolean(
    user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role),
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [planData, assetData, userData] = await Promise.all([
        request<PreventivePlan[]>("/preventive-maintenance"),
        request<Asset[]>("/assets"),
        request<UserOption[]>("/users"),
      ]);
      setPlans(planData);
      setAssets(assetData);
      setUsers(userData);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No se pudo cargar la planificacion preventiva",
      );
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredPlans = useMemo(() => {
    const term = search.trim().toLowerCase();
    return plans.filter(
      (plan) =>
        !term ||
        [plan.name, plan.asset.code, plan.asset.name, plan.assignee?.full_name]
          .filter(Boolean)
          .some((value) => value!.toLowerCase().includes(term)),
    );
  }, [plans, search]);

  const dueCount = plans.filter(
    (plan) => plan.active && new Date(plan.next_execution) <= new Date(),
  ).length;

  function openCreate() {
    setEditing(null);
    setForm({
      ...emptyForm,
      asset_id: assets[0]?.id ?? "",
      next_execution: localDateTime(new Date().toISOString()),
    });
    setModalOpen(true);
  }

  function openEdit(plan: PreventivePlan) {
    setEditing(plan);
    setForm({
      asset_id: plan.asset_id,
      assigned_to: plan.assigned_to ?? "",
      name: plan.name,
      description: plan.description,
      frequency_type: plan.frequency_type,
      frequency_value: String(plan.frequency_value),
      next_execution: localDateTime(plan.next_execution),
      estimated_duration: String(plan.estimated_duration),
      priority: plan.priority,
      active: plan.active,
    });
    setModalOpen(true);
  }

  async function savePlan(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      ...form,
      assigned_to: form.assigned_to || null,
      frequency_value: Number(form.frequency_value),
      estimated_duration: Number(form.estimated_duration),
      next_execution: new Date(form.next_execution).toISOString(),
    };
    if (editing) delete (payload as Partial<typeof payload>).asset_id;
    try {
      await request(editing ? `/preventive-maintenance/${editing.id}` : "/preventive-maintenance", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setModalOpen(false);
      setNotice(editing ? "Plan preventivo actualizado" : "Plan preventivo creado");
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar el plan");
    } finally {
      setSaving(false);
    }
  }

  async function generateOne(plan: PreventivePlan) {
    setGenerating(plan.id);
    setError("");
    setNotice("");
    try {
      await request(`/preventive-maintenance/${plan.id}/generate-work-order`, { method: "POST" });
      setNotice(`Orden preventiva generada para ${plan.asset.code}`);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo generar la orden");
    } finally {
      setGenerating("");
    }
  }

  async function generateDue() {
    setGenerating("all");
    setError("");
    setNotice("");
    try {
      const result = await request<{ generated: number; skipped: number }>(
        "/preventive-maintenance/actions/generate-due",
        { method: "POST" },
      );
      setNotice(`${result.generated} ordenes generadas, ${result.skipped} omitidas`);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron generar las ordenes");
    } finally {
      setGenerating("");
    }
  }

  return (
    <>
      <PageHeader
        title="Mantenimiento preventivo"
        description="Planes recurrentes y generacion controlada de ordenes por activo."
        actions={
          canManage ? (
            <>
              <button className="button-secondary" onClick={generateDue} disabled={generating === "all"}>
                <Play size={16} /> Generar vencidos ({dueCount})
              </button>
              <button className="button-primary" onClick={openCreate}>
                <Plus size={17} /> Nuevo plan
              </button>
            </>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="panel mb-4 flex items-center gap-3 p-3">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} />
          <input
            className="field field-with-icon"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por plan, activo o responsable"
          />
        </label>
        <div className="hidden items-center gap-2 text-xs font-bold text-[var(--muted)] sm:flex">
          <CalendarClock size={17} /> {dueCount} vencidos
        </div>
      </section>

      {loading ? (
        <LoadingBlock />
      ) : (
        <section className="panel overflow-hidden">
          {filteredPlans.length === 0 ? (
            <EmptyState title="No hay planes preventivos" detail="Registra el primer plan para un activo." />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Plan</th><th>Activo</th><th>Frecuencia</th><th>Proxima ejecucion</th><th>Responsable</th><th>Prioridad</th><th className="w-24">Acciones</th></tr>
                </thead>
                <tbody>
                  {filteredPlans.map((plan) => {
                    const overdue = plan.active && new Date(plan.next_execution) <= new Date();
                    return (
                      <tr key={plan.id}>
                        <td><p className="font-bold text-[var(--ink)]">{plan.name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{plan.active ? "Activo" : "Inactivo"}</p></td>
                        <td><p className="font-semibold text-[var(--ink)]">{plan.asset.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{plan.asset.name}</p></td>
                        <td>{frequencyLabel(plan.frequency_type, plan.frequency_value)}</td>
                        <td><span className={overdue ? "font-bold text-red-700" : ""}>{formatDate(plan.next_execution, true)}</span></td>
                        <td>{plan.assignee?.full_name ?? "Sin asignar"}</td>
                        <td><StatusBadge value={plan.priority} /></td>
                        <td>
                          {canManage && <div className="flex gap-2">
                            <button className="icon-button" onClick={() => void generateOne(plan)} disabled={Boolean(generating)} title="Generar orden" aria-label={`Generar orden para ${plan.name}`}><Wrench size={16} /></button>
                            <button className="icon-button" onClick={() => openEdit(plan)} title="Editar plan" aria-label={`Editar ${plan.name}`}><Pencil size={16} /></button>
                          </div>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <Modal open={modalOpen} title={editing ? "Editar plan preventivo" : "Nuevo plan preventivo"} description="Periodicidad, alcance y responsable de la intervencion." onClose={() => setModalOpen(false)}>
        <form onSubmit={savePlan}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Activo"><select className="field" value={form.asset_id} onChange={(event) => setForm({ ...form, asset_id: event.target.value })} disabled={Boolean(editing)} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></Field>
            <Field label="Responsable"><select className="field" value={form.assigned_to} onChange={(event) => setForm({ ...form, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((option) => <option key={option.id} value={option.id}>{option.full_name}</option>)}</select></Field>
            <div className="sm:col-span-2"><Field label="Nombre"><input className="field" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} minLength={4} maxLength={180} required /></Field></div>
            <Field label="Frecuencia"><select className="field" value={form.frequency_type} onChange={(event) => setForm({ ...form, frequency_type: event.target.value as FrequencyType })}><option value="DAYS">Dias</option><option value="WEEKS">Semanas</option><option value="MONTHS">Meses</option><option value="YEARS">Anos</option></select></Field>
            <Field label="Cada"><input className="field" type="number" min="1" max="365" value={form.frequency_value} onChange={(event) => setForm({ ...form, frequency_value: event.target.value })} required /></Field>
            <Field label="Proxima ejecucion"><input className="field" type="datetime-local" value={form.next_execution} onChange={(event) => setForm({ ...form, next_execution: event.target.value })} required /></Field>
            <Field label="Duracion estimada (min)"><input className="field" type="number" min="1" max="10080" value={form.estimated_duration} onChange={(event) => setForm({ ...form, estimated_duration: event.target.value })} required /></Field>
            <Field label="Prioridad"><select className="field" value={form.priority} onChange={(event) => setForm({ ...form, priority: event.target.value as Priority })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Estado"><select className="field" value={form.active ? "active" : "inactive"} onChange={(event) => setForm({ ...form, active: event.target.value === "active" })}><option value="active">Activo</option><option value="inactive">Inactivo</option></select></Field>
            <div className="sm:col-span-2"><Field label="Trabajo previsto"><textarea className="field" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} minLength={10} maxLength={5000} required /></Field></div>
          </div>
          <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : "Guardar plan"}</button></footer>
        </form>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function frequencyLabel(type: FrequencyType, value: number): string {
  const singular: Record<FrequencyType, string> = {
    DAYS: "dia",
    WEEKS: "semana",
    MONTHS: "mes",
    YEARS: "ano",
  };
  return `Cada ${value} ${value === 1 ? singular[type] : labelFor(type).toLowerCase()}`;
}
