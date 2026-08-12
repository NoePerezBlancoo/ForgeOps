"use client";

import { Download, FileText, Search, Trash2, Upload } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { Asset, DocumentType, TechnicalDocument } from "@/lib/types";

export default function DocumentsPage() {
  const { request, download, user } = useAuth();
  const [documents, setDocuments] = useState<TechnicalDocument[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [assetId, setAssetId] = useState("");
  const [name, setName] = useState("");
  const [documentType, setDocumentType] = useState<DocumentType>("MANUAL");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [saving, setSaving] = useState(false);
  const canManage = Boolean(
    user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role),
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [documentData, assetData] = await Promise.all([
        request<TechnicalDocument[]>("/documents"),
        request<Asset[]>("/assets"),
      ]);
      setDocuments(documentData);
      setAssets(assetData);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar la documentacion");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const filteredDocuments = useMemo(() => {
    const term = search.trim().toLowerCase();
    return documents.filter(
      (document) =>
        (!typeFilter || document.type === typeFilter) &&
        (!term ||
          [document.name, document.original_name, document.asset.code, document.asset.name]
            .some((value) => value.toLowerCase().includes(term))),
    );
  }, [documents, search, typeFilter]);

  function openUpload() {
    setAssetId(assets[0]?.id ?? "");
    setName("");
    setDocumentType("MANUAL");
    setDescription("");
    setFile(null);
    setModalOpen(true);
  }

  async function uploadDocument(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setSaving(true);
    setError("");
    const body = new FormData();
    body.set("asset_id", assetId);
    body.set("name", name);
    body.set("type", documentType);
    body.set("description", description);
    body.set("file", file);
    try {
      await request("/documents", { method: "POST", body });
      setModalOpen(false);
      setNotice("Documento tecnico almacenado");
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo subir el documento");
    } finally {
      setSaving(false);
    }
  }

  async function downloadDocument(document: TechnicalDocument) {
    setError("");
    try {
      const blob = await download(`/documents/${document.id}/download`);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.original_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo descargar el documento");
    }
  }

  async function removeDocument(document: TechnicalDocument) {
    if (!window.confirm(`Eliminar ${document.name}?`)) return;
    setError("");
    try {
      await request(`/documents/${document.id}`, { method: "DELETE" });
      setNotice("Documento eliminado");
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo eliminar el documento");
    }
  }

  return (
    <>
      <PageHeader
        title="Documentacion tecnica"
        description="Manuales, procedimientos, esquemas y registros vinculados a activos."
        actions={canManage ? <button className="button-primary" onClick={openUpload}><Upload size={17} /> Subir documento</button> : undefined}
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="panel mb-4 flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
        <label className="relative flex-1"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por documento, archivo o activo" /></label>
        <label className="sm:w-56"><select className="field" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="">Todos los tipos</option><option value="MANUAL">Manuales</option><option value="ELECTRICAL_SCHEMATIC">Esquemas electricos</option><option value="PROCEDURE">Procedimientos</option><option value="SAFETY">Seguridad</option><option value="OTHER">Otros</option></select></label>
      </section>

      {loading ? <LoadingBlock /> : <section className="panel overflow-hidden">
        {filteredDocuments.length === 0 ? <EmptyState title="No hay documentos" detail="Sube documentacion tecnica vinculada a un activo." /> : <div className="table-wrap"><table className="data-table document-table"><thead><tr><th>Documento</th><th>Activo</th><th>Tipo</th><th>Archivo</th><th>Subido por</th><th>Fecha</th><th>Acciones</th></tr></thead><tbody>
          {filteredDocuments.map((document) => <tr key={document.id}>
            <td><div className="flex min-w-0 items-center gap-3"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-cyan-50 text-cyan-800"><FileText size={17} /></div><div className="min-w-0"><p className="font-bold text-[var(--ink)]">{document.name}</p><p className="mt-1 max-w-full truncate text-[11px] text-[var(--muted)]">{document.description ?? "Sin descripcion"}</p></div></div></td>
            <td><p className="truncate font-semibold text-[var(--ink)]">{document.asset.code}</p><p className="mt-1 truncate text-[11px] text-[var(--muted)]">{document.asset.name}</p></td>
            <td>{labelFor(document.type)}</td>
            <td><p className="max-w-full truncate">{document.original_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{formatFileSize(document.file_size)}</p></td>
            <td>{document.uploader.full_name}</td>
            <td>{formatDate(document.uploaded_at, true)}</td>
            <td><div className="flex gap-2"><button className="icon-button" onClick={() => void downloadDocument(document)} title="Descargar" aria-label={`Descargar ${document.name}`}><Download size={16} /></button>{canManage && <button className="icon-button text-red-700" onClick={() => void removeDocument(document)} title="Eliminar" aria-label={`Eliminar ${document.name}`}><Trash2 size={16} /></button>}</div></td>
          </tr>)}
        </tbody></table></div>}
      </section>}

      <Modal open={modalOpen} title="Subir documento tecnico" description="El archivo quedara protegido y vinculado al activo seleccionado." onClose={() => setModalOpen(false)}>
        <form onSubmit={uploadDocument}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Activo"><select className="field" value={assetId} onChange={(event) => setAssetId(event.target.value)} required>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></Field>
          <Field label="Tipo"><select className="field" value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)}><option value="MANUAL">Manual</option><option value="ELECTRICAL_SCHEMATIC">Esquema electrico</option><option value="PROCEDURE">Procedimiento</option><option value="SAFETY">Seguridad</option><option value="OTHER">Otro</option></select></Field>
          <div className="sm:col-span-2"><Field label="Nombre"><input className="field" value={name} onChange={(event) => setName(event.target.value)} minLength={3} maxLength={180} required /></Field></div>
          <div className="sm:col-span-2"><Field label="Descripcion"><textarea className="field" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={3000} /></Field></div>
          <div className="sm:col-span-2"><Field label="Archivo"><input className="field file:mr-3 file:border-0 file:bg-transparent file:text-xs file:font-bold" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.doc,.docx,.xls,.xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></Field><p className="mt-2 text-[11px] text-[var(--muted)]">PDF, imagenes, Office o texto. Maximo 15 MB.</p></div>
        </div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4 sm:px-6"><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving || !file}>{saving ? <span className="loader loader-light" /> : "Subir documento"}</button></footer></form>
      </Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
