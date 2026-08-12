"use client";

import { CalendarDays, PlayCircle, Plus, Search, Settings2 } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { Asset, Priority, UserOption, WorkOrder, WorkOrderStatus, WorkOrderType } from "@/lib/types";

interface CreateForm {
  asset_id: string;
  assigned_to: string;
  title: string;
  description: string;
  type: WorkOrderType;
  priority: Priority;
  scheduled_date: string;
  estimated_duration: string;
}

interface ManageForm {
  assigned_to: string;
  status: WorkOrderStatus;
  priority: Priority;
  scheduled_date: string;
  estimated_duration: string;
  real_duration: string;
  observations: string;
}

const emptyCreate: CreateForm = {
  asset_id: "",
  assigned_to: "",
  title: "",
  description: "",
  type: "CORRECTIVE",
  priority: "MEDIUM",
  scheduled_date: "",
  estimated_duration: "60",
};

export default function WorkOrdersPage() {
  const { request, user } = useAuth();
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [selected, setSelected] = useState<WorkOrder | null>(null);
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
  const [manageForm, setManageForm] = useState<ManageForm | null>(null);
  const [saving, setSaving] = useState(false);

  const canCreate = user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role);
  const canManage = user && user.role !== "VIEWER";
  const isTechnician = user?.role === "TECHNICIAN";

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [orderData, assetData, userData] = await Promise.all([
        request<WorkOrder[]>("/work-orders"),
        request<Asset[]>("/assets"),
        request<UserOption[]>("/users"),
      ]);
      setOrders(orderData);
      setAssets(assetData);
      setUsers(userData.filter((item) => ["TECHNICIAN", "MAINTENANCE_MANAGER", "ADMIN"].includes(item.role)));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las ordenes");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => { void loadData(); }, [loadData]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return orders.filter((order) => {
      const matchesSearch = !term || [order.number, order.title, order.asset.code, order.asset.name].some((value) => value.toLowerCase().includes(term));
      return matchesSearch && (!statusFilter || order.status === statusFilter);
    });
  }, [orders, search, statusFilter]);

  function openCreate() {
    setCreateForm({ ...emptyCreate, asset_id: assets[0]?.id ?? "" });
    setCreateOpen(true);
  }

  function openManage(order: WorkOrder) {
    setSelected(order);
    setManageForm({
      assigned_to: order.assigned_to ?? "",
      status: order.status,
      priority: order.priority,
      scheduled_date: order.scheduled_date ? order.scheduled_date.slice(0, 16) : "",
      estimated_duration: order.estimated_duration ? String(order.estimated_duration) : "",
      real_duration: order.real_duration ? String(order.real_duration) : "",
      observations: order.observations ?? "",
    });
    setManageOpen(true);
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    const asset = assets.find((item) => item.id === createForm.asset_id);
    if (!asset) return;
    setSaving(true);
    setError("");
    try {
      await request("/work-orders", {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          plant_id: asset.plant_id,
          assigned_to: createForm.assigned_to || null,
          scheduled_date: createForm.scheduled_date ? new Date(createForm.scheduled_date).toISOString() : null,
          estimated_duration: createForm.estimated_duration ? Number(createForm.estimated_duration) : null,
        }),
      });
      setCreateOpen(false);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo crear la orden");
    } finally {
      setSaving(false);
    }
  }

  async function updateOrder(event: FormEvent) {
    event.preventDefault();
    if (!selected || !manageForm) return;
    setSaving(true);
    setError("");
    const execution = {
      status: manageForm.status,
      real_duration: manageForm.real_duration ? Number(manageForm.real_duration) : null,
      observations: manageForm.observations || null,
    };
    const payload = isTechnician ? execution : {
      ...execution,
      assigned_to: manageForm.assigned_to || null,
      priority: manageForm.priority,
      scheduled_date: manageForm.scheduled_date ? new Date(manageForm.scheduled_date).toISOString() : null,
      estimated_duration: manageForm.estimated_duration ? Number(manageForm.estimated_duration) : null,
    };
    try {
      await request(`/work-orders/${selected.id}`, { method: "PATCH", body: JSON.stringify(payload) });
      setManageOpen(false);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar la orden");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Ordenes de trabajo"
        description="Planificacion, asignacion y ejecucion del trabajo tecnico de mantenimiento."
        actions={canCreate ? <button className="button-primary" onClick={openCreate}><Plus size={17} /> Nueva orden</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row">
        <label className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por numero, tarea, activo o codigo" /></label>
        <select className="field sm:w-52" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="">Todos los estados</option><option value="OPEN">Abiertas</option><option value="ASSIGNED">Asignadas</option><option value="IN_PROGRESS">En curso</option><option value="WAITING">En espera</option><option value="COMPLETED">Completadas</option><option value="CANCELLED">Canceladas</option></select>
      </section>

      {loading ? <LoadingBlock /> : (
        <section className="panel overflow-hidden">
          {filtered.length === 0 ? <EmptyState title="No hay ordenes coincidentes" detail="Ajusta los filtros o planifica una nueva intervencion." /> : (
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Orden</th><th>Trabajo</th><th>Activo</th><th>Tipo</th><th>Prioridad</th><th>Estado</th><th>Planificada</th><th className="w-16">Accion</th></tr></thead>
                <tbody>{filtered.map((order) => (
                  <tr key={order.id}>
                    <td><p className="font-bold text-[var(--accent)]">{order.number}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{order.assignee?.full_name ?? "Sin asignar"}</p></td>
                    <td className="max-w-70"><p className="truncate font-semibold text-[var(--ink)]">{order.title}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{order.estimated_duration ? `${order.estimated_duration} min estimados` : "Sin estimacion"}</p></td>
                    <td><p className="font-semibold text-[var(--ink)]">{order.asset.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{order.asset.name}</p></td>
                    <td>{labelFor(order.type)}</td>
                    <td><StatusBadge value={order.priority} /></td>
                    <td><StatusBadge value={order.status} /></td>
                    <td><span className="inline-flex items-center gap-1.5"><CalendarDays size={14} /> {formatDate(order.scheduled_date)}</span></td>
                    <td>{canManage && <button className="icon-button" onClick={() => openManage(order)} aria-label={`Gestionar ${order.number}`}><Settings2 size={16} /></button>}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <Modal open={createOpen} title="Crear orden de trabajo" description="Define alcance, responsable y ventana de ejecucion." onClose={() => setCreateOpen(false)}>
        <form onSubmit={createOrder}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Activo"><select className="field" value={createForm.asset_id} onChange={(event) => setCreateForm({ ...createForm, asset_id: event.target.value })} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></Field>
            <Field label="Responsable"><select className="field" value={createForm.assigned_to} onChange={(event) => setCreateForm({ ...createForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
            <div className="sm:col-span-2"><Field label="Titulo"><input className="field" value={createForm.title} onChange={(event) => setCreateForm({ ...createForm, title: event.target.value })} minLength={5} required /></Field></div>
            <div className="sm:col-span-2"><Field label="Descripcion del trabajo"><textarea className="field" value={createForm.description} onChange={(event) => setCreateForm({ ...createForm, description: event.target.value })} minLength={10} required /></Field></div>
            <Field label="Tipo"><select className="field" value={createForm.type} onChange={(event) => setCreateForm({ ...createForm, type: event.target.value as WorkOrderType })}><option value="CORRECTIVE">Correctivo</option><option value="PREVENTIVE">Preventivo</option><option value="INSPECTION">Inspeccion</option><option value="IMPROVEMENT">Mejora</option></select></Field>
            <Field label="Prioridad"><select className="field" value={createForm.priority} onChange={(event) => setCreateForm({ ...createForm, priority: event.target.value as Priority })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Fecha planificada"><input className="field" type="datetime-local" value={createForm.scheduled_date} onChange={(event) => setCreateForm({ ...createForm, scheduled_date: event.target.value })} /></Field>
            <Field label="Duracion estimada (min)"><input className="field" type="number" min="1" value={createForm.estimated_duration} onChange={(event) => setCreateForm({ ...createForm, estimated_duration: event.target.value })} /></Field>
          </div>
          <ModalFooter saving={saving} onCancel={() => setCreateOpen(false)} label="Crear orden" />
        </form>
      </Modal>

      <Modal open={manageOpen} title={selected ? `${selected.number} · ${selected.title}` : "Gestionar orden"} description={selected ? `${selected.asset.code} · ${selected.asset.name}` : undefined} onClose={() => setManageOpen(false)}>
        {manageForm && <form onSubmit={updateOrder}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Estado"><select className="field" value={manageForm.status} onChange={(event) => setManageForm({ ...manageForm, status: event.target.value as WorkOrderStatus })}><option value="OPEN">Abierta</option><option value="ASSIGNED">Asignada</option><option value="IN_PROGRESS">En curso</option><option value="WAITING">En espera</option><option value="COMPLETED">Completada</option><option value="CANCELLED">Cancelada</option></select></Field>
            <Field label="Responsable"><select className="field" value={manageForm.assigned_to} onChange={(event) => setManageForm({ ...manageForm, assigned_to: event.target.value })} disabled={isTechnician}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
            <Field label="Prioridad"><select className="field" value={manageForm.priority} onChange={(event) => setManageForm({ ...manageForm, priority: event.target.value as Priority })} disabled={isTechnician}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Duracion real (min)"><input className="field" type="number" min="1" value={manageForm.real_duration} onChange={(event) => setManageForm({ ...manageForm, real_duration: event.target.value })} required={manageForm.status === "COMPLETED"} /></Field>
            <Field label="Fecha planificada"><input className="field" type="datetime-local" value={manageForm.scheduled_date} onChange={(event) => setManageForm({ ...manageForm, scheduled_date: event.target.value })} disabled={isTechnician} /></Field>
            <Field label="Duracion estimada (min)"><input className="field" type="number" min="1" value={manageForm.estimated_duration} onChange={(event) => setManageForm({ ...manageForm, estimated_duration: event.target.value })} disabled={isTechnician} /></Field>
            <div className="sm:col-span-2"><Field label="Observaciones de ejecucion"><textarea className="field" value={manageForm.observations} onChange={(event) => setManageForm({ ...manageForm, observations: event.target.value })} /></Field></div>
          </div>
          <ModalFooter saving={saving} onCancel={() => setManageOpen(false)} label="Guardar ejecucion" />
        </form>}
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function ModalFooter({ saving, onCancel, label }: { saving: boolean; onCancel: () => void; label: string }) {
  return <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={onCancel}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : <><PlayCircle size={16} /> {label}</>}</button></footer>;
}
