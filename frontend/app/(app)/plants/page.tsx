"use client";

import { Factory, MapPin, Pencil, Plus, Search } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import type { Plant } from "@/lib/types";

interface PlantForm {
  name: string;
  code: string;
  address: string;
  description: string;
  active: boolean;
}

const emptyForm: PlantForm = { name: "", code: "", address: "", description: "", active: true };

export default function PlantsPage() {
  const { request, user } = useAuth();
  const { reloadPlants } = useWorkspace();
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Plant | null>(null);
  const [form, setForm] = useState<PlantForm>(emptyForm);
  const canManage = user && ["SUPER_ADMIN", "ADMIN"].includes(user.role);

  const loadPlants = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPlants(await request<Plant[]>(`/plants?include_inactive=${canManage ? "true" : "false"}`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar las plantas");
    } finally {
      setLoading(false);
    }
  }, [canManage, request]);

  useEffect(() => {
    void loadPlants();
  }, [loadPlants]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return plants.filter((plant) => !term || [plant.name, plant.code, plant.address].filter(Boolean).some((value) => value!.toLowerCase().includes(term)));
  }, [plants, search]);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(plant: Plant) {
    setEditing(plant);
    setForm({ name: plant.name, code: plant.code, address: plant.address ?? "", description: plant.description ?? "", active: plant.active });
    setModalOpen(true);
  }

  async function savePlant(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = { ...form, address: form.address || null, description: form.description || null };
      await request(editing ? `/plants/${editing.id}` : "/plants", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(editing ? payload : { ...payload, active: undefined }),
      });
      setModalOpen(false);
      setNotice(editing ? "Planta actualizada" : "Planta creada");
      await Promise.all([loadPlants(), reloadPlants()]);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar la planta");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Plantas" description="Centros productivos que organizan activos, incidencias y carga de mantenimiento." actions={canManage ? <button className="button-primary" onClick={openCreate}><Plus size={17} /> Nueva planta</button> : undefined} />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="panel mb-4 p-3">
        <label className="relative block"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por planta, codigo o direccion" /></label>
      </section>
      {loading ? <LoadingBlock /> : (
        <section className="panel overflow-hidden">
          {filtered.length === 0 ? <EmptyState title="No hay plantas coincidentes" detail="Registra el primer centro productivo o ajusta la busqueda." /> : (
            <div className="table-wrap"><table className="data-table"><thead><tr><th>Planta</th><th>Direccion</th><th>Descripcion</th><th>Estado</th><th className="w-16">Accion</th></tr></thead><tbody>{filtered.map((plant) => <tr key={plant.id}><td><div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Factory size={17} /></div><div><p className="font-bold text-[var(--ink)]">{plant.name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{plant.code}</p></div></div></td><td><span className="inline-flex max-w-72 items-center gap-2"><MapPin className="shrink-0 text-[var(--muted)]" size={15} /><span className="truncate">{plant.address ?? "Sin direccion"}</span></span></td><td><p className="max-w-80 truncate">{plant.description ?? "Sin descripcion"}</p></td><td><StatusBadge value={plant.active ? "ACTIVE" : "OUT_OF_SERVICE"} /></td><td>{canManage && <button className="icon-button" onClick={() => openEdit(plant)} aria-label={`Editar ${plant.name}`}><Pencil size={16} /></button>}</td></tr>)}</tbody></table></div>
          )}
        </section>
      )}
      <Modal open={modalOpen} title={editing ? `Editar ${editing.code}` : "Nueva planta"} description="Centro productivo y alcance operativo." onClose={() => setModalOpen(false)}>
        <form onSubmit={savePlant}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6"><Field label="Nombre"><input className="field" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required /></Field><Field label="Codigo"><input className="field uppercase" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })} required /></Field><div className="sm:col-span-2"><Field label="Direccion"><input className="field" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} /></Field></div><div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field></div>{editing && <label className="flex items-center gap-3 rounded-md border border-[var(--line)] bg-[#fafcfb] px-4 py-3 sm:col-span-2"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /><span><strong className="block text-xs">Planta activa</strong><span className="text-[11px] text-[var(--muted)]">Las plantas con activos asociados no pueden desactivarse.</span></span></label>}</div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? "Guardando..." : "Guardar planta"}</button></footer></form>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}
