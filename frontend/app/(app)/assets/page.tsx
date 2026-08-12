"use client";

import { Pencil, Plus, Search, SlidersHorizontal } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import type { Asset, AssetStatus, Criticality, Plant } from "@/lib/types";

interface AssetForm {
  plant_id: string;
  code: string;
  name: string;
  manufacturer: string;
  model: string;
  serial_number: string;
  installation_date: string;
  status: AssetStatus;
  criticality: Criticality;
  location: string;
  description: string;
  notes: string;
}

const emptyForm: AssetForm = {
  plant_id: "",
  code: "",
  name: "",
  manufacturer: "",
  model: "",
  serial_number: "",
  installation_date: "",
  status: "ACTIVE",
  criticality: "MEDIUM",
  location: "",
  description: "",
  notes: "",
};

export default function AssetsPage() {
  const { request, user } = useAuth();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [plants, setPlants] = useState<Plant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Asset | null>(null);
  const [form, setForm] = useState<AssetForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const canManage = user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [assetData, plantData] = await Promise.all([
        request<Asset[]>("/assets"),
        request<Plant[]>("/plants"),
      ]);
      setAssets(assetData);
      setPlants(plantData);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudieron cargar los activos");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredAssets = useMemo(() => {
    const term = search.trim().toLowerCase();
    return assets.filter((asset) => {
      const matchesTerm = !term || [asset.code, asset.name, asset.location, asset.manufacturer]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(term));
      const matchesStatus = !statusFilter || asset.status === statusFilter;
      return matchesTerm && matchesStatus;
    });
  }, [assets, search, statusFilter]);

  function openCreate() {
    setEditing(null);
    setForm({ ...emptyForm, plant_id: plants[0]?.id ?? "" });
    setModalOpen(true);
  }

  function openEdit(asset: Asset) {
    setEditing(asset);
    setForm({
      plant_id: asset.plant_id,
      code: asset.code,
      name: asset.name,
      manufacturer: asset.manufacturer ?? "",
      model: asset.model ?? "",
      serial_number: asset.serial_number ?? "",
      installation_date: asset.installation_date ?? "",
      status: asset.status,
      criticality: asset.criticality,
      location: asset.location ?? "",
      description: asset.description ?? "",
      notes: asset.notes ?? "",
    });
    setModalOpen(true);
  }

  async function saveAsset(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value === "" ? null : value]),
    );
    try {
      await request(editing ? `/assets/${editing.id}` : "/assets", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setModalOpen(false);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar el activo");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Activos industriales"
        description="Inventario tecnico de maquinaria, criticidad y estado operativo por planta."
        actions={canManage ? <button className="button-primary" onClick={openCreate}><Plus size={17} /> Nuevo activo</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} />
          <input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por codigo, activo, ubicacion o fabricante" />
        </label>
        <label className="relative sm:w-52">
          <SlidersHorizontal className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={16} />
          <select className="field field-with-icon" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">Todos los estados</option>
            <option value="ACTIVE">Activos</option>
            <option value="STOPPED">Parados</option>
            <option value="MAINTENANCE">En mantenimiento</option>
            <option value="OUT_OF_SERVICE">Fuera de servicio</option>
          </select>
        </label>
      </section>

      {loading ? <LoadingBlock /> : (
        <section className="panel overflow-hidden">
          {filteredAssets.length === 0 ? <EmptyState title="No hay activos coincidentes" detail="Ajusta los filtros o registra un nuevo equipo." /> : (
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>Activo</th><th>Equipo</th><th>Ubicacion</th><th>Criticidad</th><th>Estado</th><th className="w-16">Accion</th></tr></thead>
                <tbody>
                  {filteredAssets.map((asset) => (
                    <tr key={asset.id}>
                      <td><p className="font-bold text-[var(--ink)]">{asset.code}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{asset.plant.name}</p></td>
                      <td><p className="font-semibold text-[var(--ink)]">{asset.name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{[asset.manufacturer, asset.model].filter(Boolean).join(" · ") || "Sin fabricante"}</p></td>
                      <td>{asset.location ?? "Sin ubicacion"}</td>
                      <td><StatusBadge value={asset.criticality} /></td>
                      <td><StatusBadge value={asset.status} /></td>
                      <td>{canManage && <button className="icon-button" onClick={() => openEdit(asset)} aria-label={`Editar ${asset.name}`}><Pencil size={16} /></button>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <Modal open={modalOpen} title={editing ? `Editar ${editing.code}` : "Registrar activo"} description="Datos maestros y situacion operativa del equipo." onClose={() => setModalOpen(false)}>
        <form onSubmit={saveAsset}>
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
            <Field label="Planta"><select className="field" value={form.plant_id} onChange={(event) => setForm({ ...form, plant_id: event.target.value })} required>{plants.map((plant) => <option key={plant.id} value={plant.id}>{plant.name}</option>)}</select></Field>
            <Field label="Codigo"><input className="field" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} required maxLength={50} /></Field>
            <Field label="Nombre"><input className="field" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required maxLength={160} /></Field>
            <Field label="Ubicacion"><input className="field" value={form.location} onChange={(event) => setForm({ ...form, location: event.target.value })} maxLength={160} /></Field>
            <Field label="Fabricante"><input className="field" value={form.manufacturer} onChange={(event) => setForm({ ...form, manufacturer: event.target.value })} /></Field>
            <Field label="Modelo"><input className="field" value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} /></Field>
            <Field label="Numero de serie"><input className="field" value={form.serial_number} onChange={(event) => setForm({ ...form, serial_number: event.target.value })} /></Field>
            <Field label="Fecha de instalacion"><input className="field" type="date" value={form.installation_date} onChange={(event) => setForm({ ...form, installation_date: event.target.value })} /></Field>
            <Field label="Estado"><select className="field" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as AssetStatus })}><option value="ACTIVE">Activo</option><option value="STOPPED">Parado</option><option value="MAINTENANCE">En mantenimiento</option><option value="OUT_OF_SERVICE">Fuera de servicio</option></select></Field>
            <Field label="Criticidad"><select className="field" value={form.criticality} onChange={(event) => setForm({ ...form, criticality: event.target.value as Criticality })}><option value="LOW">Baja</option><option value="MEDIUM">Media</option><option value="HIGH">Alta</option><option value="CRITICAL">Critica</option></select></Field>
            <div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field></div>
            <div className="sm:col-span-2"><Field label="Notas tecnicas"><textarea className="field" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></Field></div>
          </div>
          <footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6">
            <button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button>
            <button className="button-primary" disabled={saving}>{saving ? <span className="loader loader-light" /> : editing ? "Guardar cambios" : "Crear activo"}</button>
          </footer>
        </form>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}
