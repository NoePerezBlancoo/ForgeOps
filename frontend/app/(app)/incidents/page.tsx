"use client";

import { Clock3, Plus, Search, Settings2 } from "lucide-react";
import { FormEvent, useCallback, useDeferredValue, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { PaginationBar } from "@/components/pagination-bar";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Asset, Incident, IncidentStatus, Paginated, Priority, UserOption } from "@/lib/types";

const PAGE_SIZE = 25;

interface CreateForm {
  asset_id: string;
  assigned_to: string;
  title: string;
  description: string;
  priority: Priority;
  downtime_minutes: string;
}

interface ManageForm {
  assigned_to: string;
  status: IncidentStatus;
  priority: Priority;
  downtime_minutes: string;
  root_cause: string;
  resolution: string;
}

const emptyCreate: CreateForm = { asset_id: "", assigned_to: "", title: "", description: "", priority: "MEDIUM", downtime_minutes: "0" };

export default function IncidentsPage() {
  const { request, user } = useAuth();
  const { scopedPath } = useWorkspace();
  const [pageData, setPageData] = useState<Paginated<Incident> | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);
  const [selected, setSelected] = useState<Incident | null>(null);
  const [createForm, setCreateForm] = useState<CreateForm>(emptyCreate);
  const [manageForm, setManageForm] = useState<ManageForm | null>(null);
  const [saving, setSaving] = useState(false);
  const deepLinkHandled = useRef(false);
  const deferredSearch = useDeferredValue(search);

  const canManage = user && user.role !== "VIEWER";

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
      sort: "reported",
    });
    if (deferredSearch.trim()) params.set("search", deferredSearch.trim());
    if (statusFilter) params.set("status", statusFilter);
    try {
      setPageData(await request<Paginated<Incident>>(scopedPath(`/incidents/page?${params}`)));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las incidencias");
    } finally {
      setLoading(false);
    }
  }, [deferredSearch, page, request, scopedPath, statusFilter]);

  const loadOptions = useCallback(async () => {
    try {
      const [assetData, userData] = await Promise.all([
        request<Asset[]>(scopedPath("/assets")),
        request<UserOption[]>("/users/options"),
      ]);
      setAssets(assetData);
      setUsers(userData.filter((item) => ["TECHNICIAN", "MAINTENANCE_MANAGER", "ADMIN"].includes(item.role)));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las opciones de asignacion");
    }
  }, [request, scopedPath]);

  useEffect(() => { void loadIncidents(); }, [loadIncidents]);
  useEffect(() => { void loadOptions(); }, [loadOptions]);

  useEffect(() => {
    if (loading || !canManage || deepLinkHandled.current || assets.length === 0) return;
    if (new URLSearchParams(window.location.search).get("new") !== "1") return;
    deepLinkHandled.current = true;
    setCreateForm({ ...emptyCreate, asset_id: assets[0].id });
    setCreateOpen(true);
    window.history.replaceState({}, "", "/incidents");
  }, [assets, canManage, loading]);

  useEffect(() => {
    if (loading || !canManage || deepLinkHandled.current) return;
    const incidentId = new URLSearchParams(window.location.search).get("incident");
    if (!incidentId) return;
    deepLinkHandled.current = true;
    request<Incident>(`/incidents/${incidentId}`).then((incident) => {
      setSelected(incident);
      setManageForm({
        assigned_to: incident.assigned_to ?? "",
        status: incident.status,
        priority: incident.priority,
        downtime_minutes: String(incident.downtime_minutes),
        root_cause: incident.root_cause ?? "",
        resolution: incident.resolution ?? "",
      });
      setManageOpen(true);
    }).catch((requestError) => {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo abrir la incidencia");
    });
    window.history.replaceState({}, "", "/incidents");
  }, [canManage, loading, request]);

  const incidents = pageData?.items ?? [];

  function openCreate() {
    setCreateForm({ ...emptyCreate, asset_id: assets[0]?.id ?? "" });
    setCreateOpen(true);
  }

  function openManage(incident: Incident) {
    setSelected(incident);
    setManageForm({
      assigned_to: incident.assigned_to ?? "",
      status: incident.status,
      priority: incident.priority,
      downtime_minutes: String(incident.downtime_minutes),
      root_cause: incident.root_cause ?? "",
      resolution: incident.resolution ?? "",
    });
    setManageOpen(true);
  }

  async function createIncident(event: FormEvent) {
    event.preventDefault();
    const asset = assets.find((item) => item.id === createForm.asset_id);
    if (!asset) return;
    setSaving(true);
    setError("");
    try {
      await request("/incidents", {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          plant_id: asset.plant_id,
          assigned_to: createForm.assigned_to || null,
          downtime_minutes: Number(createForm.downtime_minutes || 0),
        }),
      });
      setCreateOpen(false);
      await loadIncidents();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo registrar la incidencia");
    } finally {
      setSaving(false);
    }
  }

  async function updateIncident(event: FormEvent) {
    event.preventDefault();
    if (!selected || !manageForm) return;
    setSaving(true);
    setError("");
    try {
      await request(`/incidents/${selected.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          ...manageForm,
          assigned_to: manageForm.assigned_to || null,
          downtime_minutes: Number(manageForm.downtime_minutes || 0),
          root_cause: manageForm.root_cause || null,
          resolution: manageForm.resolution || null,
        }),
      });
      setManageOpen(false);
      await loadIncidents();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar la incidencia");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Incidencias"
        description="Registro, asignacion y resolucion trazable de averias y desviaciones de planta."
        actions={canManage ? <button className="button-primary" onClick={openCreate}><Plus size={17} /> Nueva incidencia</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row">
        <label className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Buscar por incidencia, activo o codigo" /></label>
        <select className="field sm:w-52" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}><option value="">Todos los estados</option><option value="OPEN">Abiertas</option><option value="ASSIGNED">Asignadas</option><option value="IN_PROGRESS">En curso</option><option value="WAITING">En espera</option><option value="RESOLVED">Resueltas</option><option value="CLOSED">Cerradas</option></select>
      </section>

      {loading ? <LoadingBlock /> : (
        <section className="panel overflow-hidden">
          {incidents.length === 0 ? <EmptyState title="No hay incidencias coincidentes" detail="Ajusta los filtros o registra un nuevo evento de planta." /> : (
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Incidencia</th><th>Activo</th><th>Prioridad</th><th>Estado</th><th>Asignacion</th><th>Parada</th><th className="w-16">Accion</th></tr></thead>
                <tbody>{incidents.map((incident) => (
                  <tr key={incident.id}>
                    <td className="max-w-75"><p className="truncate font-bold text-[var(--ink)]">{incident.title}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{formatDate(incident.reported_at, true)}</p></td>
                    <td><p className="font-semibold text-[var(--ink)]">{incident.asset.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{incident.asset.name}</p></td>
                    <td><StatusBadge value={incident.priority} /></td>
                    <td><StatusBadge value={incident.status} /></td>
                    <td>{incident.assignee?.full_name ?? "Sin asignar"}</td>
                    <td><span className="inline-flex items-center gap-1.5"><Clock3 size={14} /> {incident.downtime_minutes} min</span></td>
                    <td>{canManage && <button className="icon-button" onClick={() => openManage(incident)} aria-label={`Gestionar ${incident.title}`}><Settings2 size={16} /></button>}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          {pageData && <PaginationBar noun="incidencias" page={pageData.page} pages={pageData.pages} total={pageData.total} onPageChange={setPage} />}
        </section>
      )}

      <Modal open={createOpen} title="Registrar incidencia" description="Documenta el problema y asigna una primera respuesta." onClose={() => setCreateOpen(false)}>
        <form onSubmit={createIncident}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Activo"><select className="field" value={createForm.asset_id} onChange={(event) => setCreateForm({ ...createForm, asset_id: event.target.value })} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></Field>
            <Field label="Asignar a"><select className="field" value={createForm.assigned_to} onChange={(event) => setCreateForm({ ...createForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
            <div className="sm:col-span-2"><Field label="Titulo"><input className="field" value={createForm.title} onChange={(event) => setCreateForm({ ...createForm, title: event.target.value })} minLength={5} maxLength={180} required /></Field></div>
            <div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={createForm.description} onChange={(event) => setCreateForm({ ...createForm, description: event.target.value })} minLength={10} required /></Field></div>
            <Field label="Prioridad"><select className="field" value={createForm.priority} onChange={(event) => setCreateForm({ ...createForm, priority: event.target.value as Priority })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Parada inicial (min)"><input className="field" type="number" min="0" value={createForm.downtime_minutes} onChange={(event) => setCreateForm({ ...createForm, downtime_minutes: event.target.value })} /></Field>
          </div>
          <ModalFooter saving={saving} onCancel={() => setCreateOpen(false)} label="Registrar incidencia" />
        </form>
      </Modal>

      <Modal open={manageOpen} title={selected?.title ?? "Gestionar incidencia"} description={selected ? `${selected.asset.code} · ${selected.asset.name}` : undefined} onClose={() => setManageOpen(false)}>
        {manageForm && <form onSubmit={updateIncident}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Estado"><select className="field" value={manageForm.status} onChange={(event) => setManageForm({ ...manageForm, status: event.target.value as IncidentStatus })}><option value="OPEN">Abierta</option><option value="ASSIGNED">Asignada</option><option value="IN_PROGRESS">En curso</option><option value="WAITING">En espera</option><option value="RESOLVED">Resuelta</option><option value="CLOSED">Cerrada</option></select></Field>
            <Field label="Responsable"><select className="field" value={manageForm.assigned_to} onChange={(event) => setManageForm({ ...manageForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
            <Field label="Prioridad"><select className="field" value={manageForm.priority} onChange={(event) => setManageForm({ ...manageForm, priority: event.target.value as Priority })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <Field label="Parada acumulada (min)"><input className="field" type="number" min="0" value={manageForm.downtime_minutes} onChange={(event) => setManageForm({ ...manageForm, downtime_minutes: event.target.value })} /></Field>
            <div className="sm:col-span-2"><Field label="Causa raiz"><textarea className="field" value={manageForm.root_cause} onChange={(event) => setManageForm({ ...manageForm, root_cause: event.target.value })} /></Field></div>
            <div className="sm:col-span-2"><Field label="Resolucion"><textarea className="field" value={manageForm.resolution} onChange={(event) => setManageForm({ ...manageForm, resolution: event.target.value })} required={["RESOLVED", "CLOSED"].includes(manageForm.status)} /></Field></div>
          </div>
          <ModalFooter saving={saving} onCancel={() => setManageOpen(false)} label="Guardar seguimiento" />
        </form>}
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function ModalFooter({ saving, onCancel, label }: { saving: boolean; onCancel: () => void; label: string }) {
  return <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={onCancel}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : label}</button></footer>;
}
