"use client";

import { AlertTriangle, ArrowDownToLine, History, PackagePlus, Pencil, Search } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type {
  InventoryItem,
  InventoryMovement,
  InventoryMovementType,
} from "@/lib/types";

interface ItemForm {
  code: string;
  name: string;
  description: string;
  stock: string;
  minimum_stock: string;
  unit: string;
  location: string;
  cost: string;
  active: boolean;
}

const emptyItem: ItemForm = {
  code: "",
  name: "",
  description: "",
  stock: "0",
  minimum_stock: "0",
  unit: "ud",
  location: "",
  cost: "",
  active: true,
};

export default function InventoryPage() {
  const { request, user } = useAuth();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [onlyLowStock, setOnlyLowStock] = useState(false);
  const [itemModal, setItemModal] = useState(false);
  const [editing, setEditing] = useState<InventoryItem | null>(null);
  const [itemForm, setItemForm] = useState<ItemForm>(emptyItem);
  const [movementItem, setMovementItem] = useState<InventoryItem | null>(null);
  const [movementType, setMovementType] = useState<InventoryMovementType>("RECEIPT");
  const [quantity, setQuantity] = useState("1");
  const [reason, setReason] = useState("");
  const [historyItem, setHistoryItem] = useState<InventoryItem | null>(null);
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [saving, setSaving] = useState(false);
  const loadSequence = useRef(0);
  const canManage = Boolean(
    user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role),
  );

  const loadItems = useCallback(async () => {
    const sequence = ++loadSequence.current;
    setLoading(true);
    setError("");
    try {
      const loaded = await request<InventoryItem[]>("/inventory");
      if (sequence === loadSequence.current) setItems(loaded);
    } catch (requestError) {
      if (sequence === loadSequence.current) {
        setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el inventario");
      }
    } finally {
      if (sequence === loadSequence.current) setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadItems();
  }, [loadItems]);

  const filteredItems = useMemo(() => {
    const term = search.trim().toLowerCase();
    return items.filter(
      (item) =>
        (!onlyLowStock || item.low_stock) &&
        (!term || [item.code, item.name, item.location].filter(Boolean).some((value) => value!.toLowerCase().includes(term))),
    );
  }, [items, onlyLowStock, search]);

  const inventoryValue = items.reduce(
    (total, item) => total + Number(item.stock) * Number(item.cost ?? 0),
    0,
  );
  const lowStockCount = items.filter((item) => item.low_stock).length;

  function openCreate() {
    setEditing(null);
    setItemForm(emptyItem);
    setItemModal(true);
  }

  function openEdit(item: InventoryItem) {
    setEditing(item);
    setItemForm({
      code: item.code,
      name: item.name,
      description: item.description ?? "",
      stock: item.stock,
      minimum_stock: item.minimum_stock,
      unit: item.unit,
      location: item.location ?? "",
      cost: item.cost ?? "",
      active: item.active,
    });
    setItemModal(true);
  }

  async function saveItem(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload: Record<string, string | number | boolean | null> = {
      ...itemForm,
      stock: Number(itemForm.stock),
      minimum_stock: Number(itemForm.minimum_stock),
      cost: itemForm.cost ? Number(itemForm.cost) : null,
      description: itemForm.description || null,
      location: itemForm.location || null,
    };
    if (editing) {
      delete payload.stock;
      payload.expected_version = editing.version;
    }
    try {
      await request(editing ? `/inventory/${editing.id}` : "/inventory", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setItemModal(false);
      setNotice(editing ? "Repuesto actualizado" : "Repuesto registrado");
      await loadItems();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar el repuesto");
    } finally {
      setSaving(false);
    }
  }

  function openMovement(item: InventoryItem) {
    setMovementItem(item);
    setMovementType("RECEIPT");
    setQuantity("1");
    setReason("");
  }

  async function saveMovement(event: FormEvent) {
    event.preventDefault();
    if (!movementItem) return;
    setSaving(true);
    setError("");
    try {
      await request(`/inventory/${movementItem.id}/movements`, {
        method: "POST",
        body: JSON.stringify({
          movement_type: movementType,
          quantity: Number(quantity),
          reason,
          expected_version: movementItem.version,
        }),
      });
      setMovementItem(null);
      setNotice("Movimiento de stock registrado");
      await loadItems();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo registrar el movimiento");
      if (requestError instanceof ApiError && requestError.status === 409) {
        setMovementItem(null);
        await loadItems();
      }
    } finally {
      setSaving(false);
    }
  }

  async function openHistory(item: InventoryItem) {
    setError("");
    setHistoryItem(item);
    setMovements([]);
    try {
      setMovements(await request<InventoryMovement[]>(`/inventory/${item.id}/movements`));
    } catch (requestError) {
      setHistoryItem(null);
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el historial");
    }
  }

  return (
    <>
      <PageHeader
        title="Inventario de repuestos"
        description="Stock disponible, niveles minimos y movimientos trazables."
        actions={canManage ? <button className="button-primary" onClick={openCreate}><PackagePlus size={17} /> Nuevo repuesto</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="mb-4 grid gap-3 sm:grid-cols-3">
        <article className="panel p-4"><p className="text-[11px] font-bold uppercase text-[var(--muted)]">Referencias activas</p><p className="mt-2 text-2xl font-bold">{items.filter((item) => item.active).length}</p></article>
        <article className="panel p-4"><p className="text-[11px] font-bold uppercase text-[var(--muted)]">Bajo stock minimo</p><p className="mt-2 text-2xl font-bold text-red-700">{lowStockCount}</p></article>
        <article className="panel p-4"><p className="text-[11px] font-bold uppercase text-[var(--muted)]">Valor de inventario</p><p className="mt-2 text-2xl font-bold">{inventoryValue.toLocaleString("es-ES", { style: "currency", currency: "EUR" })}</p></article>
      </section>
      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
        <label className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por codigo, nombre o ubicacion" /></label>
        <label className="flex min-h-10 items-center gap-2 px-2 text-xs font-bold text-[var(--ink-soft)]"><input type="checkbox" checked={onlyLowStock} onChange={(event) => setOnlyLowStock(event.target.checked)} /> Solo bajo minimo</label>
      </section>

      {loading ? <LoadingBlock /> : <section className="panel overflow-hidden">
        {filteredItems.length === 0 ? <EmptyState title="No hay repuestos coincidentes" detail="Ajusta los filtros o registra una referencia." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Referencia</th><th>Descripcion</th><th>Ubicacion</th><th>Stock</th><th>Minimo</th><th>Coste</th><th className="w-32">Acciones</th></tr></thead><tbody>
          {filteredItems.map((item) => <tr key={item.id}>
            <td><p className="font-bold text-[var(--ink)]">{item.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{item.active ? "Activo" : "Inactivo"}</p></td>
            <td><p className="font-semibold text-[var(--ink)]">{item.name}</p><p className="mt-1 max-w-80 truncate text-[11px] text-[var(--muted)]">{item.description ?? "Sin descripcion"}</p></td>
            <td>{item.location ?? "Sin ubicar"}</td>
            <td><span className={`inline-flex items-center gap-1.5 font-bold ${item.low_stock ? "text-red-700" : "text-[var(--ink)]"}`}>{item.low_stock && <AlertTriangle size={14} />}{Number(item.stock).toLocaleString("es-ES")} {item.unit}</span></td>
            <td>{Number(item.minimum_stock).toLocaleString("es-ES")} {item.unit}</td>
            <td>{item.cost ? Number(item.cost).toLocaleString("es-ES", { style: "currency", currency: "EUR" }) : "-"}</td>
            <td><div className="flex gap-2">{canManage && <><button className="icon-button" onClick={() => openMovement(item)} title="Registrar movimiento" aria-label={`Movimiento de ${item.code}`}><ArrowDownToLine size={16} /></button><button className="icon-button" onClick={() => openEdit(item)} title="Editar repuesto" aria-label={`Editar ${item.code}`}><Pencil size={16} /></button></>}<button className="icon-button" onClick={() => void openHistory(item)} title="Ver historial" aria-label={`Historial de ${item.code}`}><History size={16} /></button></div></td>
          </tr>)}
        </tbody></table></div>}
      </section>}

      <Modal open={itemModal} title={editing ? `Editar ${editing.code}` : "Nuevo repuesto"} description="Ficha maestra y parametros de aprovisionamiento." onClose={() => setItemModal(false)}>
        <form onSubmit={saveItem}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Codigo"><input className="field" value={itemForm.code} onChange={(event) => setItemForm({ ...itemForm, code: event.target.value })} minLength={2} maxLength={60} required /></Field>
          <Field label="Nombre"><input className="field" value={itemForm.name} onChange={(event) => setItemForm({ ...itemForm, name: event.target.value })} minLength={3} maxLength={180} required /></Field>
          {!editing && <Field label="Stock inicial"><input className="field" type="number" min="0" step="0.001" value={itemForm.stock} onChange={(event) => setItemForm({ ...itemForm, stock: event.target.value })} required /></Field>}
          <Field label="Stock minimo"><input className="field" type="number" min="0" step="0.001" value={itemForm.minimum_stock} onChange={(event) => setItemForm({ ...itemForm, minimum_stock: event.target.value })} required /></Field>
          <Field label="Unidad"><input className="field" value={itemForm.unit} onChange={(event) => setItemForm({ ...itemForm, unit: event.target.value })} maxLength={24} required /></Field>
          <Field label="Coste unitario"><input className="field" type="number" min="0" step="0.01" value={itemForm.cost} onChange={(event) => setItemForm({ ...itemForm, cost: event.target.value })} /></Field>
          <Field label="Ubicacion"><input className="field" value={itemForm.location} onChange={(event) => setItemForm({ ...itemForm, location: event.target.value })} maxLength={160} /></Field>
          <Field label="Estado"><select className="field" value={itemForm.active ? "active" : "inactive"} onChange={(event) => setItemForm({ ...itemForm, active: event.target.value === "active" })}><option value="active">Activo</option><option value="inactive">Inactivo</option></select></Field>
          <div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={itemForm.description} onChange={(event) => setItemForm({ ...itemForm, description: event.target.value })} maxLength={3000} /></Field></div>
        </div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={() => setItemModal(false)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : "Guardar repuesto"}</button></footer></form>
      </Modal>

      <Modal open={Boolean(movementItem)} title={`Movimiento de ${movementItem?.code ?? "stock"}`} description={movementItem ? `Disponible: ${Number(movementItem.stock).toLocaleString("es-ES")} ${movementItem.unit}` : undefined} onClose={() => setMovementItem(null)}>
        <form onSubmit={saveMovement}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Tipo"><select className="field" value={movementType} onChange={(event) => setMovementType(event.target.value as InventoryMovementType)}><option value="RECEIPT">Entrada</option><option value="CONSUMPTION">Consumo</option><option value="ADJUSTMENT">Ajuste</option></select></Field>
          <Field label="Cantidad"><input className="field" type="number" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} required /></Field>
          <div className="sm:col-span-2"><Field label="Motivo"><input className="field" value={reason} onChange={(event) => setReason(event.target.value)} minLength={4} maxLength={255} required /></Field></div>
        </div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={() => setMovementItem(null)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : "Registrar movimiento"}</button></footer></form>
      </Modal>

      <Modal open={Boolean(historyItem)} title={`Historial de ${historyItem?.code ?? "repuesto"}`} description="Ultimos movimientos registrados." onClose={() => setHistoryItem(null)}>
        <div className="max-h-[60vh] divide-y divide-[var(--line)] overflow-y-auto">{movements.length === 0 ? <EmptyState title="Sin movimientos" detail="Esta referencia todavia no tiene movimientos." /> : movements.map((movement) => <div key={movement.id} className="flex items-start gap-3 px-5 py-4 sm:px-6"><div className={`grid size-9 shrink-0 place-items-center rounded-md ${Number(movement.quantity) >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"}`}>{Number(movement.quantity) >= 0 ? "+" : "-"}</div><div className="min-w-0 flex-1"><p className="text-xs font-bold text-[var(--ink)]">{labelFor(movement.movement_type)} · {movement.reason}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{movement.user.full_name} · {formatDate(movement.created_at, true)}</p>{movement.work_order_id && <Link className="mt-1 inline-block text-[11px] font-bold text-[var(--accent)] hover:underline" href={`/work-orders?order=${movement.work_order_id}`}>Ver orden vinculada</Link>}</div><div className="shrink-0 text-right"><p className="text-sm font-bold">{Number(movement.quantity) > 0 ? "+" : ""}{Number(movement.quantity).toLocaleString("es-ES")} {movement.item.unit}</p><p className="text-[10px] text-[var(--muted)]">Stock {Number(movement.resulting_stock).toLocaleString("es-ES")}</p>{movement.work_order_id && <p className="mt-1 text-[10px] font-semibold text-[var(--ink-soft)]">{formatCurrency(Math.abs(Number(movement.total_cost)))}</p>}</div></div>)}</div>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function formatCurrency(value: number) {
  return value.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
}
