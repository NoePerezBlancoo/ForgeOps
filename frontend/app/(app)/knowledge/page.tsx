"use client";

import {
  BookOpenCheck,
  BrainCircuit,
  Database,
  Download,
  FileSearch,
  RefreshCw,
  Send,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { useWorkspace } from "@/components/workspace-provider";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type {
  Asset,
  KnowledgeAnswer,
  KnowledgeHistory,
  KnowledgeSource,
  KnowledgeStatus,
  TechnicalDocument,
} from "@/lib/types";

interface Exchange {
  question: string;
  response: KnowledgeAnswer;
}

const suggestions = [
  "Como se debe realizar el bloqueo de energias antes de intervenir?",
  "Que comprobaciones indica la documentacion del compresor?",
  "Que pasos de diagnostico se recomiendan para el robot de soldadura?",
];

export default function KnowledgePage() {
  const { request, download, user } = useAuth();
  const { scopedPath } = useWorkspace();
  const [status, setStatus] = useState<KnowledgeStatus | null>(null);
  const [documents, setDocuments] = useState<TechnicalDocument[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [history, setHistory] = useState<KnowledgeHistory[]>([]);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [question, setQuestion] = useState("");
  const [assetId, setAssetId] = useState("");
  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);
  const [indexing, setIndexing] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const conversationEnd = useRef<HTMLDivElement>(null);
  const canManage = Boolean(
    user && ["SUPER_ADMIN", "ADMIN", "MAINTENANCE_MANAGER"].includes(user.role),
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statusData, documentData, assetData, historyData] = await Promise.all([
        request<KnowledgeStatus>("/ai/status"),
        request<TechnicalDocument[]>(scopedPath("/documents")),
        request<Asset[]>(scopedPath("/assets")),
        request<KnowledgeHistory[]>("/ai/history?limit=8"),
      ]);
      setStatus(statusData);
      setDocuments(documentData);
      setAssets(assetData);
      setHistory(historyData);
    } catch (requestError) {
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : "No se pudo cargar la base de conocimiento",
      );
    } finally {
      setLoading(false);
    }
  }, [request, scopedPath]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [exchanges, asking]);

  async function ask(event: FormEvent) {
    event.preventDefault();
    const cleanQuestion = question.trim();
    if (cleanQuestion.length < 5) return;
    setAsking(true);
    setError("");
    setNotice("");
    try {
      const response = await request<KnowledgeAnswer>("/ai/query", {
        method: "POST",
        body: JSON.stringify({
          question: cleanQuestion,
          asset_id: assetId || null,
          top_k: 5,
        }),
      });
      setExchanges((current) => [...current, { question: cleanQuestion, response }]);
      setQuestion("");
      const updatedHistory = await request<KnowledgeHistory[]>("/ai/history?limit=8");
      setHistory(updatedHistory);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo consultar la documentacion");
    } finally {
      setAsking(false);
    }
  }

  async function indexAll(force = false) {
    setIndexing("all");
    setError("");
    setNotice("");
    try {
      const result = await request<{ indexed: number; failed: number; unsupported: number }>(
        `/ai/documents/index?force=${force}`,
        { method: "POST" },
      );
      setNotice(
        `${result.indexed} documentos indexados, ${result.failed} con error y ${result.unsupported} no compatibles`,
      );
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo actualizar el indice");
    } finally {
      setIndexing("");
    }
  }

  async function indexOne(document: TechnicalDocument) {
    setIndexing(document.id);
    setError("");
    setNotice("");
    try {
      const result = await request<{ status: string; message: string }>(
        `/ai/documents/${document.id}/index?force=true`,
        { method: "POST" },
      );
      setNotice(result.message);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo indexar el documento");
    } finally {
      setIndexing("");
    }
  }

  async function downloadSource(source: KnowledgeSource) {
    setError("");
    try {
      const blob = await download(`/documents/${source.document_id}/download`);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = source.original_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo descargar la fuente");
    }
  }

  if (loading && !status) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        title="Asistente documental"
        description="Consulta procedimientos y manuales con evidencia vinculada a los documentos de planta."
        actions={
          status ? (
            <div className="flex items-center gap-2 rounded-md border border-[var(--line)] bg-white px-3 py-2 text-xs font-bold text-[var(--ink-soft)]">
              <span className={`size-2 rounded-full ${status.generation_available ? "bg-emerald-500" : "bg-amber-500"}`} />
              {status.generation_available ? `RAG | ${status.chat_model}` : "Recuperacion local"}
            </div>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      {status?.configuration_warning && (
        <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-800">
          {status.configuration_warning}
        </div>
      )}

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
        <article className="panel flex min-h-[560px] min-w-0 flex-col overflow-hidden xl:h-[calc(100vh-190px)]">
          <header className="flex items-center gap-3 border-b border-[var(--line)] px-5 py-4">
            <div className="grid size-9 place-items-center rounded-md bg-cyan-50 text-cyan-800"><BrainCircuit size={19} /></div>
            <div className="min-w-0 flex-1">
              <h3 className="text-sm font-bold">Consulta tecnica</h3>
              <p className="mt-1 text-[11px] text-[var(--muted)]">{assetId ? "Contexto limitado al activo seleccionado" : "Contexto de toda la empresa"}</p>
            </div>
            <ShieldCheck className="text-emerald-700" size={19} />
          </header>

          <div className="flex-1 space-y-6 overflow-y-auto bg-[#fafcfb] p-4 sm:p-6">
            {exchanges.length === 0 && (
              <div className="grid min-h-96 place-items-center text-center">
                <div className="max-w-xl">
                  <div className="mx-auto grid size-12 place-items-center rounded-md bg-[var(--ink)] text-white"><BookOpenCheck size={23} /></div>
                  <h3 className="mt-4 text-lg font-bold">Consulta la base documental</h3>
                  <p className="mx-auto mt-2 max-w-md text-sm text-[var(--muted)]">Las respuestas muestran sus fuentes y avisan cuando la evidencia indexada no es suficiente.</p>
                  <div className="mt-5 grid gap-2 text-left">
                    {suggestions.map((suggestion) => <button key={suggestion} className="rounded-md border border-[var(--line)] bg-white px-4 py-3 text-left text-xs font-semibold text-[var(--ink-soft)] hover:border-[#aebbb7] hover:text-[var(--ink)]" onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}
                  </div>
                </div>
              </div>
            )}

            {exchanges.map((exchange) => (
              <div key={exchange.response.query_id} className="space-y-4">
                <div className="ml-auto max-w-[82%] rounded-md bg-[var(--ink)] px-4 py-3 text-sm leading-6 text-white">{exchange.question}</div>
                <div className="border-l-2 border-[var(--accent)] pl-4 sm:pl-5">
                  <div className="mb-3 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase text-[var(--muted)]">
                    <span>{modeLabel(exchange.response.mode)}</span><span>·</span><span>{Math.round(exchange.response.confidence * 100)}% confianza</span><span>·</span><span>{exchange.response.duration_ms} ms</span>
                  </div>
                  <div className="whitespace-pre-wrap text-sm leading-6 text-[var(--ink)]">{exchange.response.answer}</div>
                  {exchange.response.sources.length > 0 && (
                    <div className="mt-5 border-t border-[var(--line)] pt-3">
                      <p className="mb-2 text-[10px] font-bold uppercase text-[var(--muted)]">Fuentes consultadas</p>
                      <div className="divide-y divide-[var(--line)]">
                        {exchange.response.sources.map((source, index) => (
                          <div key={source.chunk_id} className="flex min-w-0 gap-3 py-3">
                            <span className="grid size-7 shrink-0 place-items-center rounded bg-cyan-50 text-[11px] font-bold text-cyan-800">{index + 1}</span>
                            <div className="min-w-0 flex-1"><p className="truncate text-xs font-bold">{source.document_name}</p><p className="mt-1 text-[10px] font-semibold text-[var(--muted)]">{source.asset_code} · {source.asset_name}{source.page_number ? ` · Pagina ${source.page_number}` : ""}</p><p className="mt-2 line-clamp-2 text-[11px] leading-4 text-[var(--ink-soft)]">{source.excerpt}</p></div>
                            <button className="icon-button" onClick={() => void downloadSource(source)} title="Descargar fuente" aria-label={`Descargar ${source.document_name}`}><Download size={15} /></button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {asking && <div className="flex items-center gap-3 border-l-2 border-[var(--accent)] pl-4 text-sm font-semibold text-[var(--muted)]"><span className="loader" /> Consultando evidencia</div>}
            <div ref={conversationEnd} />
          </div>

          <form onSubmit={ask} className="border-t border-[var(--line)] bg-white p-4 sm:p-5">
            <div className="mb-3 flex items-center gap-3">
              <label className="flex-1"><span className="sr-only">Activo</span><select className="field" value={assetId} onChange={(event) => setAssetId(event.target.value)}><option value="">Todos los activos</option>{assets.map((asset) => <option key={asset.id} value={asset.id}>{asset.code} · {asset.name}</option>)}</select></label>
              <span className="hidden text-[10px] font-bold uppercase text-[var(--muted)] sm:block">{status?.chunks ?? 0} fragmentos disponibles</span>
            </div>
            <div className="flex items-end gap-2">
              <textarea className="field min-h-20 flex-1" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Pregunta sobre un procedimiento, averia o manual..." minLength={5} maxLength={1000} required />
              <button className="button-primary h-10 px-3" disabled={asking || question.trim().length < 5} aria-label="Enviar consulta" title="Enviar consulta"><Send size={18} /></button>
            </div>
          </form>
        </article>

        <div className="space-y-5">
          <article className="panel overflow-hidden">
            <header className="flex items-center gap-3 border-b border-[var(--line)] px-4 py-4">
              <Database size={18} className="text-cyan-800" />
              <div className="min-w-0 flex-1"><h3 className="text-sm font-bold">Base documental</h3><p className="mt-1 text-[11px] text-[var(--muted)]">Estado de indexacion</p></div>
              {canManage && <button className="icon-button" onClick={() => void indexAll(false)} disabled={Boolean(indexing)} title="Indexar pendientes" aria-label="Indexar documentos pendientes"><RefreshCw className={indexing === "all" ? "animate-spin" : ""} size={16} /></button>}
            </header>
            {status && <div className="grid grid-cols-3 divide-x divide-[var(--line)] border-b border-[var(--line)]"><Metric value={status.indexed_documents} label="Listos" /><Metric value={status.chunks} label="Fragmentos" /><Metric value={status.pending_documents + status.failed_documents} label="Pendientes" /></div>}
            <div className="max-h-[390px] divide-y divide-[var(--line)] overflow-y-auto">
              {documents.length === 0 ? <div className="px-4 py-8 text-center text-xs text-[var(--muted)]">No hay documentos registrados.</div> : documents.map((document) => (
                <div key={document.id} className="flex min-w-0 items-center gap-3 px-4 py-3.5">
                  <div className="grid size-8 shrink-0 place-items-center rounded-md bg-[#f0f5f3] text-[var(--ink-soft)]"><FileSearch size={16} /></div>
                  <div className="min-w-0 flex-1"><p className="truncate text-xs font-bold">{document.name}</p><div className="mt-1 flex items-center gap-2"><StatusBadge value={document.index_status} /><span className="truncate text-[10px] text-[var(--muted)]">{document.chunk_count} fragmentos</span></div>{document.index_error && <p className="mt-1 line-clamp-2 text-[10px] leading-4 text-red-700">{document.index_error}</p>}</div>
                  {canManage && document.index_status !== "UNSUPPORTED" && <button className="icon-button" onClick={() => void indexOne(document)} disabled={Boolean(indexing)} title="Reindexar" aria-label={`Reindexar ${document.name}`}><RefreshCw className={indexing === document.id ? "animate-spin" : ""} size={15} /></button>}
                </div>
              ))}
            </div>
          </article>

          <article className="panel overflow-hidden">
            <header className="border-b border-[var(--line)] px-4 py-4"><h3 className="text-sm font-bold">Consultas recientes</h3><p className="mt-1 text-[11px] text-[var(--muted)]">Historial personal</p></header>
            <div className="max-h-72 divide-y divide-[var(--line)] overflow-y-auto">{history.length === 0 ? <div className="px-4 py-8 text-center text-xs text-[var(--muted)]">Todavia no hay consultas.</div> : history.map((item) => <button key={item.id} className="block w-full px-4 py-3 text-left hover:bg-[#fafcfb]" onClick={() => setQuestion(item.question)}><p className="line-clamp-2 text-xs font-semibold leading-4 text-[var(--ink)]">{item.question}</p><p className="mt-1 text-[10px] text-[var(--muted)]">{formatDate(item.created_at, true)} · {item.source_count} fuentes</p></button>)}</div>
          </article>
        </div>
      </section>
    </>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return <div className="px-2 py-3 text-center"><p className="text-lg font-bold text-[var(--ink)]">{value}</p><p className="mt-1 text-[9px] font-bold uppercase text-[var(--muted)]">{label}</p></div>;
}

function modeLabel(mode: KnowledgeAnswer["mode"]): string {
  if (mode === "generative") return "Respuesta RAG";
  if (mode === "extractive") return "Respuesta extractiva";
  return "Evidencia insuficiente";
}
