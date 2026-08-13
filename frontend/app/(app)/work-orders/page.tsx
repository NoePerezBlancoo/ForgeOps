"use client";

import {
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  Eye,
  FileCheck2,
  MessageSquarePlus,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Search,
  ShieldCheck,
  Square,
  Trash2,
  UserPlus,
  Users,
  Wrench,
} from "lucide-react";
import { FormEvent, useCallback, useDeferredValue, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { PaginationBar } from "@/components/pagination-bar";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { formatDate, initials, labelFor } from "@/lib/format";
import type {
  Asset,
  Paginated,
  Priority,
  UserOption,
  WorkOrder,
  WorkOrderDetail,
  WorkOrderEventType,
  WorkOrderNoteType,
  WorkOrderParticipantRole,
  WorkOrderStatus,
  WorkOrderType,
} from "@/lib/types";

const PAGE_SIZE = 25;
type DialogName = "create" | "edit" | "team" | "note" | "complete" | "validate" | "close" | "reopen" | null;

const emptyCreate = {
  asset_id: "",
  assigned_to: "",
  title: "",
  description: "",
  type: "CORRECTIVE" as WorkOrderType,
  priority: "MEDIUM" as Priority,
  scheduled_date: "",
  estimated_duration: "60",
};

const emptyComplete = {
  work_performed: "",
  failure_cause: "",
  root_cause: "",
  resolution: "",
  observations: "",
};

export default function WorkOrdersPage() {
  const { request, user } = useAuth();
  const { plantsLoading, scopedPath } = useWorkspace();
  const [pageData, setPageData] = useState<Paginated<WorkOrder> | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [users, setUsers] = useState<UserOption[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WorkOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [dialog, setDialog] = useState<DialogName>(null);
  const [saving, setSaving] = useState(false);
  const [acting, setActing] = useState("");
  const [createForm, setCreateForm] = useState(emptyCreate);
  const [editForm, setEditForm] = useState({ assigned_to: "", priority: "MEDIUM" as Priority, scheduled_date: "", estimated_duration: "", observations: "" });
  const [teamForm, setTeamForm] = useState({ user_id: "", role: "TECHNICIAN" as WorkOrderParticipantRole });
  const [noteForm, setNoteForm] = useState({ note_type: "COMMENT" as WorkOrderNoteType, body: "" });
  const [completeForm, setCompleteForm] = useState(emptyComplete);
  const [reviewNote, setReviewNote] = useState("");
  const detailRef = useRef<HTMLElement>(null);
  const deepLinkHandled = useRef(false);
  const deferredSearch = useDeferredValue(search);

  const isManager = Boolean(user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role));
  const canAct = user?.role !== "VIEWER";

  const loadOrders = useCallback(async () => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), sort: "created" });
    if (deferredSearch.trim()) params.set("search", deferredSearch.trim());
    if (statusFilter) params.set("status", statusFilter);
    try {
      const loaded = await request<Paginated<WorkOrder>>(scopedPath(`/work-orders/page?${params}`));
      setPageData(loaded);
      const requestedOrder = !deepLinkHandled.current
        ? new URLSearchParams(window.location.search).get("order")
        : null;
      if (requestedOrder) {
        deepLinkHandled.current = true;
        setSelectedId(requestedOrder);
        window.history.replaceState({}, "", "/work-orders");
        return;
      }
      setSelectedId((current) =>
        current && loaded.items.some((item) => item.id === current)
          ? current
          : (loaded.items[0]?.id ?? null),
      );
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudieron cargar las ordenes"));
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
      setUsers(userData.filter((item) => item.active && ["TECHNICIAN", "MAINTENANCE_MANAGER", "ADMIN", "SUPER_ADMIN"].includes(item.role)));
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudieron cargar las opciones"));
    }
  }, [request, scopedPath]);

  const loadDetail = useCallback(async (orderId: string) => {
    setDetailLoading(true);
    setError("");
    try {
      setDetail(await request<WorkOrderDetail>(`/work-orders/${orderId}`));
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo cargar la intervencion"));
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [request]);

  useEffect(() => {
    if (!plantsLoading) void loadOrders();
  }, [loadOrders, plantsLoading]);
  useEffect(() => {
    if (!plantsLoading) void loadOptions();
  }, [loadOptions, plantsLoading]);
  useEffect(() => {
    if (selectedId) void loadDetail(selectedId);
    else setDetail(null);
  }, [loadDetail, selectedId]);

  const mutate = useCallback(async (path: string, body: Record<string, unknown>, action: string) => {
    if (!detail) return false;
    setActing(action);
    setError("");
    try {
      const updated = await request<WorkOrderDetail>(`/work-orders/${detail.id}/${path}`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setDetail(updated);
      setDialog(null);
      await loadOrders();
      return true;
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo completar la accion"));
      return false;
    } finally {
      setActing("");
    }
  }, [detail, loadOrders, request]);

  function openCreate() {
    setCreateForm({ ...emptyCreate, asset_id: assets[0]?.id ?? "" });
    setDialog("create");
  }

  function openEdit() {
    if (!detail) return;
    setEditForm({
      assigned_to: detail.assigned_to ?? "",
      priority: detail.priority,
      scheduled_date: detail.scheduled_date ? detail.scheduled_date.slice(0, 16) : "",
      estimated_duration: detail.estimated_duration ? String(detail.estimated_duration) : "",
      observations: detail.observations ?? "",
    });
    setDialog("edit");
  }

  async function createOrder(event: FormEvent) {
    event.preventDefault();
    const asset = assets.find((item) => item.id === createForm.asset_id);
    if (!asset) return;
    setSaving(true);
    setError("");
    try {
      const created = await request<WorkOrderDetail>("/work-orders", {
        method: "POST",
        body: JSON.stringify({
          ...createForm,
          plant_id: asset.plant_id,
          assigned_to: createForm.assigned_to || null,
          scheduled_date: createForm.scheduled_date ? new Date(createForm.scheduled_date).toISOString() : null,
          estimated_duration: createForm.estimated_duration ? Number(createForm.estimated_duration) : null,
        }),
      });
      setSelectedId(created.id);
      setDetail(created);
      setDialog(null);
      await loadOrders();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo crear la orden"));
    } finally {
      setSaving(false);
    }
  }

  async function updateOrder(event: FormEvent) {
    event.preventDefault();
    if (!detail) return;
    setSaving(true);
    setError("");
    try {
      const updated = await request<WorkOrderDetail>(`/work-orders/${detail.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          assigned_to: editForm.assigned_to || null,
          priority: editForm.priority,
          scheduled_date: editForm.scheduled_date ? new Date(editForm.scheduled_date).toISOString() : null,
          estimated_duration: editForm.estimated_duration ? Number(editForm.estimated_duration) : null,
          observations: editForm.observations || null,
        }),
      });
      setDetail(updated);
      setDialog(null);
      await loadOrders();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo actualizar la orden"));
    } finally {
      setSaving(false);
    }
  }

  async function addTeamMember(event: FormEvent) {
    event.preventDefault();
    if (!detail || !teamForm.user_id) return;
    setSaving(true);
    await mutate("participants", teamForm, "team");
    setSaving(false);
  }

  async function removeTeamMember(participantId: string) {
    if (!detail || !window.confirm("Retirar este participante de la intervencion?")) return;
    setActing(`remove-${participantId}`);
    try {
      const updated = await request<WorkOrderDetail>(`/work-orders/${detail.id}/participants/${participantId}`, { method: "DELETE" });
      setDetail(updated);
      await loadOrders();
    } catch (requestError) {
      setError(messageFor(requestError, "No se pudo retirar al participante"));
    } finally {
      setActing("");
    }
  }

  async function addWorkNote(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    const succeeded = await mutate("notes", noteForm, "note");
    setSaving(false);
    if (succeeded) setNoteForm({ note_type: "COMMENT", body: "" });
  }

  async function completeWork(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    const succeeded = await mutate("complete", completeForm, "complete");
    setSaving(false);
    if (succeeded) setCompleteForm(emptyComplete);
  }

  async function submitReview(event: FormEvent) {
    event.preventDefault();
    if (!dialog) return;
    setSaving(true);
    const succeeded = dialog === "reopen"
      ? await mutate("reopen", { reason: reviewNote }, "reopen")
      : await mutate(dialog, { note: reviewNote || null }, dialog);
    setSaving(false);
    if (succeeded) setReviewNote("");
  }

  const orders = pageData?.items ?? [];
  const activeParticipant = detail?.participants.find((item) => item.active && item.user_id === user?.id);
  const openSession = detail?.sessions.find((item) => item.user_id === user?.id && !item.ended_at);
  const operational = Boolean(detail && ["OPEN", "ASSIGNED", "IN_PROGRESS", "WAITING"].includes(detail.status));
  const canStart = Boolean(canAct && detail && operational && activeParticipant && !openSession);
  const canPause = Boolean(canAct && openSession);
  const canComplete = Boolean(canAct && detail && operational && activeParticipant && (isManager || activeParticipant.role === "LEAD" || detail.assigned_to === user?.id));
  const canNote = Boolean(canAct && (isManager || activeParticipant));
  const availableUsers = users.filter((candidate) => !detail?.participants.some((participant) => participant.active && participant.user_id === candidate.id));

  function selectOrder(orderId: string) {
    setSelectedId(orderId);
    if (window.matchMedia("(max-width: 1279px)").matches) {
      window.requestAnimationFrame(() => detailRef.current?.scrollIntoView({ behavior: "smooth" }));
    }
  }

  return (
    <>
      <PageHeader
        title="Ordenes de trabajo"
        description="Intervenciones, responsables, tiempos y validacion del mantenimiento."
        actions={isManager ? <button className="button-primary" onClick={openCreate}><Plus size={17} /> Nueva orden</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}

      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} />
          <input className="field field-with-icon" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Numero, trabajo o activo" />
        </label>
        <select className="field sm:w-56" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }} aria-label="Filtrar por estado">
          <option value="">Todos los estados</option>
          <option value="OPEN">Abiertas</option>
          <option value="ASSIGNED">Asignadas</option>
          <option value="IN_PROGRESS">En curso</option>
          <option value="WAITING">En espera</option>
          <option value="PENDING_VALIDATION">Pendientes de validacion</option>
          <option value="COMPLETED">Completadas</option>
          <option value="CLOSED">Cerradas</option>
        </select>
      </section>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(560px,1.25fr)_minmax(360px,0.75fr)]">
        {loading ? <LoadingBlock /> : (
          <section className="panel overflow-hidden">
            {orders.length === 0 ? <EmptyState title="Sin ordenes" detail="No hay resultados para los filtros activos." /> : (
              <>
                <div className="hidden table-wrap md:block">
                  <table className="data-table work-orders-table">
                    <thead><tr><th>Orden</th><th>Trabajo / activo</th><th>Situacion</th><th>Plan</th><th><span className="sr-only">Detalle</span></th></tr></thead>
                    <tbody>{orders.map((order) => (
                      <tr key={order.id} className={selectedId === order.id ? "bg-[#f3f8f6]" : ""}>
                        <td><button className="text-left font-bold text-[var(--accent)]" onClick={() => selectOrder(order.id)}>{order.number}</button><p className="mt-1 text-[11px] text-[var(--muted)]">{order.assignee?.full_name ?? "Sin asignar"}</p></td>
                        <td><button className="block w-full truncate text-left font-semibold text-[var(--ink)]" onClick={() => selectOrder(order.id)}>{order.title}</button><p className="mt-1 truncate text-[11px] text-[var(--muted)]">{order.asset.code} · {order.asset.name} · {labelFor(order.type)}</p></td>
                        <td><div className="flex flex-col items-start gap-1.5"><StatusBadge value={order.status} /><StatusBadge value={order.priority} /></div></td>
                        <td><span className="inline-flex items-center gap-1.5 text-xs"><CalendarDays size={14} /> {formatDate(order.scheduled_date)}</span></td>
                        <td><button className="icon-button" onClick={() => selectOrder(order.id)} aria-label={`Ver ${order.number}`}><Eye size={16} /></button></td>
                      </tr>
                    ))}</tbody>
                  </table>
                </div>
                <div className="divide-y divide-[var(--line)] md:hidden">
                  {orders.map((order) => (
                    <button key={order.id} className={`flex w-full items-center gap-3 p-4 text-left ${selectedId === order.id ? "bg-[#f3f8f6]" : "bg-white"}`} onClick={() => selectOrder(order.id)}>
                      <div className="min-w-0 flex-1"><div className="flex items-center gap-2"><span className="text-xs font-bold text-[var(--accent)]">{order.number}</span><StatusBadge value={order.priority} /></div><p className="mt-2 truncate text-sm font-bold">{order.title}</p><p className="mt-1 truncate text-xs text-[var(--muted)]">{order.asset.code} · {order.assignee?.full_name ?? "Sin asignar"}</p></div>
                      <div className="shrink-0 text-right"><StatusBadge value={order.status} /><ChevronRight className="ml-auto mt-3 text-[var(--muted)]" size={17} /></div>
                    </button>
                  ))}
                </div>
              </>
            )}
            {pageData && <PaginationBar noun="ordenes" page={pageData.page} pages={pageData.pages} total={pageData.total} onPageChange={setPage} />}
          </section>
        )}

        <aside ref={detailRef} className="panel scroll-mt-24 overflow-hidden xl:sticky xl:top-22">
          {detailLoading ? <LoadingBlock /> : detail ? (
            <WorkOrderDetailPanel
              detail={detail}
              userId={user?.id}
              isManager={isManager}
              canStart={canStart}
              canPause={canPause}
              canComplete={canComplete}
              canNote={canNote}
              acting={acting}
              onEdit={openEdit}
              onTeam={() => { setTeamForm({ user_id: availableUsers[0]?.id ?? "", role: "TECHNICIAN" }); setDialog("team"); }}
              onNote={() => setDialog("note")}
              onStart={() => void mutate(detail.sessions.some((item) => item.user_id === user?.id) ? "resume" : "start", {}, "start")}
              onPause={() => void mutate("pause", {}, "pause")}
              onComplete={() => setDialog("complete")}
              onValidate={() => setDialog("validate")}
              onClose={() => setDialog("close")}
              onReopen={() => setDialog("reopen")}
              onRemoveParticipant={(participantId) => void removeTeamMember(participantId)}
            />
          ) : <EmptyState title="Sin detalle disponible" detail="No hay una intervencion activa en esta vista." />}
        </aside>
      </div>

      <Modal open={dialog === "create"} title="Nueva orden de trabajo" description="Alcance inicial de la intervencion" onClose={() => setDialog(null)}>
        <form onSubmit={createOrder}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Activo"><select className="field" value={createForm.asset_id} onChange={(event) => setCreateForm({ ...createForm, asset_id: event.target.value })} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></Field>
          <Field label="Tecnico principal"><select className="field" value={createForm.assigned_to} onChange={(event) => setCreateForm({ ...createForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
          <div className="sm:col-span-2"><Field label="Titulo"><input className="field" value={createForm.title} onChange={(event) => setCreateForm({ ...createForm, title: event.target.value })} minLength={5} required /></Field></div>
          <div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={createForm.description} onChange={(event) => setCreateForm({ ...createForm, description: event.target.value })} minLength={10} required /></Field></div>
          <Field label="Tipo"><select className="field" value={createForm.type} onChange={(event) => setCreateForm({ ...createForm, type: event.target.value as WorkOrderType })}><option value="CORRECTIVE">Correctivo</option><option value="PREVENTIVE">Preventivo</option><option value="INSPECTION">Inspeccion</option><option value="IMPROVEMENT">Mejora</option></select></Field>
          <Field label="Prioridad"><PrioritySelect value={createForm.priority} onChange={(priority) => setCreateForm({ ...createForm, priority })} /></Field>
          <Field label="Fecha planificada"><input className="field" type="datetime-local" value={createForm.scheduled_date} onChange={(event) => setCreateForm({ ...createForm, scheduled_date: event.target.value })} /></Field>
          <Field label="Duracion estimada"><input className="field" type="number" min="1" value={createForm.estimated_duration} onChange={(event) => setCreateForm({ ...createForm, estimated_duration: event.target.value })} /></Field>
        </div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label="Crear orden" icon={<Plus size={16} />} /></form>
      </Modal>

      <Modal open={dialog === "edit"} title={detail ? `Editar ${detail.number}` : "Editar orden"} onClose={() => setDialog(null)}>
        <form onSubmit={updateOrder}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Tecnico principal"><select className="field" value={editForm.assigned_to} onChange={(event) => setEditForm({ ...editForm, assigned_to: event.target.value })}><option value="">Sin asignar</option>{users.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
          <Field label="Prioridad"><PrioritySelect value={editForm.priority} onChange={(priority) => setEditForm({ ...editForm, priority })} /></Field>
          <Field label="Fecha planificada"><input className="field" type="datetime-local" value={editForm.scheduled_date} onChange={(event) => setEditForm({ ...editForm, scheduled_date: event.target.value })} /></Field>
          <Field label="Duracion estimada"><input className="field" type="number" min="1" value={editForm.estimated_duration} onChange={(event) => setEditForm({ ...editForm, estimated_duration: event.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Observaciones"><textarea className="field" value={editForm.observations} onChange={(event) => setEditForm({ ...editForm, observations: event.target.value })} /></Field></div>
        </div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label="Guardar" icon={<Pencil size={16} />} /></form>
      </Modal>

      <Modal open={dialog === "team"} title="Incorporar participante" description={detail?.number} onClose={() => setDialog(null)}>
        <form onSubmit={addTeamMember}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Profesional"><select className="field" value={teamForm.user_id} onChange={(event) => setTeamForm({ ...teamForm, user_id: event.target.value })} required><option value="">Seleccionar</option>{availableUsers.map((item) => <option key={item.id} value={item.id}>{item.full_name}</option>)}</select></Field>
          <Field label="Funcion"><select className="field" value={teamForm.role} onChange={(event) => setTeamForm({ ...teamForm, role: event.target.value as WorkOrderParticipantRole })}><option value="LEAD">Tecnico principal</option><option value="TECHNICIAN">Tecnico</option><option value="SUPPORT">Apoyo</option></select></Field>
        </div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label="Incorporar" icon={<UserPlus size={16} />} /></form>
      </Modal>

      <Modal open={dialog === "note"} title="Registrar nota" description={detail?.number} onClose={() => setDialog(null)}>
        <form onSubmit={addWorkNote}><div className="space-y-4 p-5 sm:p-6">
          <Field label="Tipo"><select className="field" value={noteForm.note_type} onChange={(event) => setNoteForm({ ...noteForm, note_type: event.target.value as WorkOrderNoteType })}><option value="COMMENT">Comentario</option><option value="MEASUREMENT">Medicion</option><option value="WORK_LOG">Trabajo realizado</option><option value="CAUSE">Causa</option><option value="SOLUTION">Solucion</option></select></Field>
          <Field label="Detalle"><textarea className="field min-h-32" value={noteForm.body} onChange={(event) => setNoteForm({ ...noteForm, body: event.target.value })} minLength={2} required /></Field>
        </div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label="Registrar" icon={<MessageSquarePlus size={16} />} /></form>
      </Modal>

      <Modal open={dialog === "complete"} title="Finalizar intervencion" description={detail?.number} onClose={() => setDialog(null)}>
        <form onSubmit={completeWork}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <div className="sm:col-span-2"><Field label="Trabajo realizado"><textarea className="field min-h-28" value={completeForm.work_performed} onChange={(event) => setCompleteForm({ ...completeForm, work_performed: event.target.value })} minLength={10} required /></Field></div>
          <Field label="Causa"><textarea className="field" value={completeForm.failure_cause} onChange={(event) => setCompleteForm({ ...completeForm, failure_cause: event.target.value })} required={detail?.type === "CORRECTIVE"} /></Field>
          <Field label="Causa raiz"><textarea className="field" value={completeForm.root_cause} onChange={(event) => setCompleteForm({ ...completeForm, root_cause: event.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Solucion"><textarea className="field" value={completeForm.resolution} onChange={(event) => setCompleteForm({ ...completeForm, resolution: event.target.value })} required={detail?.type === "CORRECTIVE"} /></Field></div>
          <div className="sm:col-span-2"><Field label="Observaciones"><textarea className="field" value={completeForm.observations} onChange={(event) => setCompleteForm({ ...completeForm, observations: event.target.value })} /></Field></div>
        </div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label="Finalizar" icon={<Square size={15} />} /></form>
      </Modal>

      <Modal open={["validate", "close", "reopen"].includes(dialog ?? "")} title={dialog === "validate" ? "Validar trabajo" : dialog === "close" ? "Cerrar orden" : "Reabrir orden"} description={detail?.number} onClose={() => setDialog(null)}>
        <form onSubmit={submitReview}><div className="p-5 sm:p-6"><Field label={dialog === "reopen" ? "Motivo" : "Observacion"}><textarea className="field min-h-28" value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} required={dialog === "reopen"} minLength={dialog === "reopen" ? 5 : 2} /></Field></div><ModalFooter saving={saving} onCancel={() => setDialog(null)} label={dialog === "validate" ? "Validar" : dialog === "close" ? "Cerrar" : "Reabrir"} icon={dialog === "reopen" ? <RotateCcw size={16} /> : <ShieldCheck size={16} />} /></form>
      </Modal>
    </>
  );
}

function WorkOrderDetailPanel({ detail, userId, isManager, canStart, canPause, canComplete, canNote, acting, onEdit, onTeam, onNote, onStart, onPause, onComplete, onValidate, onClose, onReopen, onRemoveParticipant }: {
  detail: WorkOrderDetail;
  userId?: string;
  isManager: boolean;
  canStart: boolean;
  canPause: boolean;
  canComplete: boolean;
  canNote: boolean;
  acting: string;
  onEdit: () => void;
  onTeam: () => void;
  onNote: () => void;
  onStart: () => void;
  onPause: () => void;
  onComplete: () => void;
  onValidate: () => void;
  onClose: () => void;
  onReopen: () => void;
  onRemoveParticipant: (participantId: string) => void;
}) {
  const hasPreviousSession = detail.sessions.some((item) => item.user_id === userId);
  const activeParticipants = detail.participants.filter((item) => item.active);
  const teamEditable = ["OPEN", "ASSIGNED", "IN_PROGRESS", "WAITING"].includes(detail.status);
  return (
    <div>
      <header className="border-b border-[var(--line)] p-5">
        <div className="flex items-start gap-3"><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="text-xs font-bold text-[var(--accent)]">{detail.number}</span><StatusBadge value={detail.priority} /><StatusBadge value={detail.status} /></div><h2 className="mt-2 text-lg font-bold text-[var(--ink)]">{detail.title}</h2><p className="mt-1 text-sm text-[var(--muted)]">{detail.asset.code} · {detail.asset.name}</p></div>{isManager && teamEditable && <button className="icon-button" onClick={onEdit} aria-label="Editar orden" title="Editar"><Pencil size={16} /></button>}</div>
        <div className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-[var(--line)] bg-[var(--line)]">
          <Metric label="Tipo" value={labelFor(detail.type)} />
          <Metric label="Planificada" value={formatDate(detail.scheduled_date)} />
          <Metric label="Estimacion" value={detail.estimated_duration ? `${detail.estimated_duration} min` : "Sin dato"} />
          <Metric label="Tiempo total" value={detail.real_duration ? `${detail.real_duration} min` : "En curso"} />
        </div>
      </header>

      {(canStart || canPause || canComplete || canNote || (isManager && ["PENDING_VALIDATION", "COMPLETED", "CLOSED"].includes(detail.status))) && (
        <div className="flex flex-wrap gap-2 border-b border-[var(--line)] bg-[#fafcfb] p-4">
          {canStart && <button className="button-primary" disabled={Boolean(acting)} onClick={onStart}><Play size={16} /> {hasPreviousSession ? "Reanudar" : "Empezar"}</button>}
          {canPause && <button className="button-secondary" disabled={Boolean(acting)} onClick={onPause}><Pause size={16} /> Pausar</button>}
          {canComplete && <button className="button-secondary" onClick={onComplete}><Square size={15} /> Finalizar</button>}
          {canNote && <button className="button-secondary" onClick={onNote}><MessageSquarePlus size={16} /> Nota</button>}
          {isManager && detail.status === "PENDING_VALIDATION" && <button className="button-primary" onClick={onValidate}><ShieldCheck size={16} /> Validar</button>}
          {isManager && detail.status === "COMPLETED" && <button className="button-primary" onClick={onClose}><FileCheck2 size={16} /> Cerrar</button>}
          {isManager && ["PENDING_VALIDATION", "COMPLETED", "CLOSED"].includes(detail.status) && <button className="button-secondary" onClick={onReopen}><RotateCcw size={16} /> Reabrir</button>}
        </div>
      )}

      <section className="border-b border-[var(--line)] p-5">
        <p className="text-xs font-bold uppercase text-[var(--muted)]">Descripcion</p>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[var(--ink-soft)]">{detail.description}</p>
        {(detail.work_performed || detail.failure_cause || detail.root_cause || detail.resolution) && <div className="mt-5 grid gap-4 sm:grid-cols-2"><DetailText label="Trabajo realizado" value={detail.work_performed} /><DetailText label="Causa" value={detail.failure_cause} /><DetailText label="Causa raiz" value={detail.root_cause} /><DetailText label="Solucion" value={detail.resolution} /></div>}
      </section>

      <section className="border-b border-[var(--line)] p-5">
        <div className="flex items-center justify-between"><div className="flex items-center gap-2"><Users size={17} className="text-[var(--accent)]" /><h3 className="text-sm font-bold">Equipo</h3><span className="text-xs text-[var(--muted)]">{activeParticipants.length}</span></div>{isManager && teamEditable && <button className="icon-button" onClick={onTeam} aria-label="Incorporar participante" title="Incorporar"><UserPlus size={16} /></button>}</div>
        <div className="mt-3 divide-y divide-[var(--line)]">
          {activeParticipants.map((participant) => <div key={participant.id} className="flex items-center gap-3 py-3"><div className="grid size-8 shrink-0 place-items-center rounded-md bg-[var(--ink)] text-[10px] font-bold text-white">{initials(participant.user.full_name)}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{participant.user.full_name}</p><p className="text-xs text-[var(--muted)]">{labelFor(participant.role)}</p></div>{participant.user_id === userId && detail.sessions.some((session) => session.user_id === userId && !session.ended_at) && <span className="size-2 rounded-full bg-emerald-500" title="Trabajando" />}{isManager && teamEditable && <button className="icon-button size-8" disabled={acting === `remove-${participant.id}`} onClick={() => onRemoveParticipant(participant.id)} aria-label={`Retirar a ${participant.user.full_name}`}><Trash2 size={14} /></button>}</div>)}
        </div>
      </section>

      {detail.sessions.length > 0 && <section className="border-b border-[var(--line)] p-5"><div className="flex items-center gap-2"><Clock3 size={17} className="text-[var(--accent)]" /><h3 className="text-sm font-bold">Tiempos</h3></div><div className="mt-3 divide-y divide-[var(--line)]">{detail.sessions.map((session) => <div key={session.id} className="flex items-center justify-between gap-3 py-2.5 text-xs"><div className="min-w-0"><p className="truncate font-semibold text-[var(--ink)]">{session.user.full_name}</p><p className="mt-1 text-[var(--muted)]">{formatDate(session.started_at, true)} · {session.ended_reason ? labelFor(session.ended_reason) : "En curso"}</p></div><span className="shrink-0 font-bold text-[var(--ink-soft)]">{durationLabel(session.duration_seconds)}</span></div>)}</div></section>}

      {detail.notes.length > 0 && <section className="border-b border-[var(--line)] p-5"><div className="flex items-center gap-2"><MessageSquarePlus size={17} className="text-[var(--accent)]" /><h3 className="text-sm font-bold">Notas</h3></div><div className="mt-3 space-y-3">{detail.notes.slice().reverse().map((note) => <article key={note.id} className="border-l-2 border-[var(--accent)] pl-3"><div className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]"><span className="font-bold text-[var(--ink-soft)]">{note.author?.full_name ?? "Usuario historico"}</span><span>{labelFor(note.note_type)}</span><span>{formatDate(note.created_at, true)}</span></div><p className="mt-1 whitespace-pre-wrap text-sm leading-5">{note.body}</p></article>)}</div></section>}

      <section className="p-5"><div className="flex items-center gap-2"><CircleDot size={17} className="text-[var(--accent)]" /><h3 className="text-sm font-bold">Historial</h3></div><div className="relative mt-4 space-y-0 before:absolute before:bottom-3 before:left-[7px] before:top-3 before:w-px before:bg-[var(--line)]">{detail.events.slice().reverse().map((event) => <div key={event.id} className="relative flex gap-3 pb-4"><span className="relative z-10 mt-1 grid size-[15px] shrink-0 place-items-center rounded-full border-2 border-[var(--accent)] bg-white" /><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><TimelineIcon type={event.event_type} /><p className="text-sm font-semibold">{event.summary}</p></div><p className="mt-1 text-[11px] text-[var(--muted)]">{formatDate(event.occurred_at, true)}{event.actor ? ` · ${event.actor.full_name}` : ""}</p></div></div>)}</div></section>
    </div>
  );
}

function TimelineIcon({ type }: { type: WorkOrderEventType }) {
  const Icon = type === "STARTED" || type === "RESUMED" ? Play : type === "PAUSED" ? Pause : type === "COMPLETED" || type === "CLOSED" ? CheckCircle2 : type === "VALIDATED" ? ShieldCheck : type === "PARTICIPANT_ADDED" || type === "ASSIGNED" ? UserPlus : type === "REOPENED" ? RotateCcw : type === "UPDATED" ? Pencil : Wrench;
  return <Icon className="shrink-0 text-[var(--muted)]" size={13} />;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="min-w-0 bg-white px-3 py-2.5"><p className="text-[10px] font-bold uppercase text-[var(--muted)]">{label}</p><p className="mt-1 truncate text-xs font-semibold text-[var(--ink)]">{value}</p></div>; }
function DetailText({ label, value }: { label: string; value: string | null }) { return value ? <div><p className="text-[10px] font-bold uppercase text-[var(--muted)]">{label}</p><p className="mt-1 whitespace-pre-wrap text-sm leading-5">{value}</p></div> : null; }
function durationLabel(seconds: number | null) { if (seconds === null) return "Activo"; if (seconds < 60) return `${seconds} s`; const hours = Math.floor(seconds / 3600); const minutes = Math.floor((seconds % 3600) / 60); return hours ? `${hours} h ${minutes} min` : `${minutes} min`; }
function messageFor(error: unknown, fallback: string) { return error instanceof ApiError ? error.message : fallback; }
function Field({ label, children }: { label: string; children: React.ReactNode }) { return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>; }
function PrioritySelect({ value, onChange }: { value: Priority; onChange: (value: Priority) => void }) { return <select className="field" value={value} onChange={(event) => onChange(event.target.value as Priority)}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select>; }
function ModalFooter({ saving, onCancel, label, icon }: { saving: boolean; onCancel: () => void; label: string; icon: React.ReactNode }) { return <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={onCancel}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : <>{icon} {label}</>}</button></footer>; }
