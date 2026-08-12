"use client";

import { Building2, CheckCircle2, Globe2, Mail, MapPin, Phone, Save } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ErrorBanner, LoadingBlock } from "@/components/feedback";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import type { Company } from "@/lib/types";

interface CompanyForm {
  name: string;
  tax_id: string;
  industry: string;
  email: string;
  phone: string;
  address: string;
  timezone: string;
  locale: string;
  work_order_prefix: string;
}

const emptyForm: CompanyForm = {
  name: "",
  tax_id: "",
  industry: "",
  email: "",
  phone: "",
  address: "",
  timezone: "Europe/Madrid",
  locale: "es-ES",
  work_order_prefix: "OT",
};

export default function CompanyPage() {
  const { request, user } = useAuth();
  const [company, setCompany] = useState<Company | null>(null);
  const [form, setForm] = useState<CompanyForm>(emptyForm);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const canManage = user && ["SUPER_ADMIN", "ADMIN"].includes(user.role);

  const loadCompany = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const loaded = await request<Company>("/companies/current");
      setCompany(loaded);
      setForm({
        name: loaded.name,
        tax_id: loaded.tax_id,
        industry: loaded.industry ?? "",
        email: loaded.email ?? "",
        phone: loaded.phone ?? "",
        address: loaded.address ?? "",
        timezone: loaded.timezone,
        locale: loaded.locale,
        work_order_prefix: loaded.work_order_prefix,
      });
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar la empresa");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => {
    void loadCompany();
  }, [loadCompany]);

  const completeness = useMemo(() => {
    const fields = [form.name, form.tax_id, form.industry, form.email, form.phone, form.address];
    return Math.round((fields.filter((value) => value.trim()).length / fields.length) * 100);
  }, [form]);

  async function saveCompany(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value.trim() || null]),
      );
      const updated = await request<Company>("/companies/current", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      setCompany(updated);
      setNotice("Configuracion empresarial guardada");
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar la empresa");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingBlock />;

  return (
    <>
      <PageHeader
        title="Empresa"
        description="Identidad corporativa y convenciones que utiliza ForgeOps en la operacion diaria."
        actions={
          company?.active ? (
            <span className="status-badge badge-success"><CheckCircle2 size={13} /> Empresa activa</span>
          ) : undefined
        }
      />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}

      <section className="mb-5 grid gap-4 md:grid-cols-3">
        <article className="panel flex items-center gap-4 p-4">
          <div className="grid size-10 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Building2 size={20} /></div>
          <div><p className="text-[11px] font-bold uppercase text-[var(--muted)]">Organizacion</p><p className="mt-1 text-sm font-bold">{company?.name}</p></div>
        </article>
        <article className="panel flex items-center gap-4 p-4">
          <div className="grid size-10 place-items-center rounded-md bg-emerald-50 text-emerald-700"><Globe2 size={20} /></div>
          <div><p className="text-[11px] font-bold uppercase text-[var(--muted)]">Zona operativa</p><p className="mt-1 text-sm font-bold">{form.timezone}</p></div>
        </article>
        <article className="panel p-4">
          <div className="flex items-center justify-between text-[11px] font-bold uppercase text-[var(--muted)]"><span>Perfil completado</span><strong className="text-[var(--ink)]">{completeness}%</strong></div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#edf0ef]"><div className="h-full bg-[var(--accent)]" style={{ width: `${completeness}%` }} /></div>
        </article>
      </section>

      <form onSubmit={saveCompany} className="panel overflow-hidden">
        <header className="border-b border-[var(--line)] px-5 py-4 sm:px-6">
          <h3 className="text-sm font-bold">Datos corporativos</h3>
          <p className="mt-1 text-xs text-[var(--muted)]">Informacion visible para administradores y utilizada en documentos operativos.</p>
        </header>
        <div className="grid gap-5 p-5 sm:grid-cols-2 sm:p-6">
          <Field label="Razon social"><input className="field" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required disabled={!canManage} /></Field>
          <Field label="Identificador fiscal"><input className="field" value={form.tax_id} onChange={(event) => setForm({ ...form, tax_id: event.target.value })} required disabled={!canManage} /></Field>
          <Field label="Sector industrial"><input className="field" value={form.industry} onChange={(event) => setForm({ ...form, industry: event.target.value })} placeholder="Metal, alimentacion, automocion..." disabled={!canManage} /></Field>
          <Field label="Correo corporativo"><div className="relative"><Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={16} /><input className="field field-with-icon" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} disabled={!canManage} /></div></Field>
          <Field label="Telefono"><div className="relative"><Phone className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={16} /><input className="field field-with-icon" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} disabled={!canManage} /></div></Field>
          <Field label="Prefijo de ordenes"><input className="field uppercase" value={form.work_order_prefix} onChange={(event) => setForm({ ...form, work_order_prefix: event.target.value.toUpperCase() })} maxLength={8} required disabled={!canManage} /></Field>
          <div className="sm:col-span-2"><Field label="Direccion"><div className="relative"><MapPin className="absolute left-3 top-3 text-[var(--muted)]" size={16} /><textarea className="field field-with-icon" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} disabled={!canManage} /></div></Field></div>
          <Field label="Zona horaria"><select className="field" value={form.timezone} onChange={(event) => setForm({ ...form, timezone: event.target.value })} disabled={!canManage}><option value="Europe/Madrid">Europe/Madrid</option><option value="Europe/Lisbon">Europe/Lisbon</option><option value="UTC">UTC</option><option value="America/Mexico_City">America/Mexico_City</option><option value="America/Bogota">America/Bogota</option></select></Field>
          <Field label="Idioma regional"><select className="field" value={form.locale} onChange={(event) => setForm({ ...form, locale: event.target.value })} disabled={!canManage}><option value="es-ES">Espanol (Espana)</option><option value="pt-PT">Portugues (Portugal)</option><option value="en-GB">English (UK)</option><option value="es-MX">Espanol (Mexico)</option></select></Field>
        </div>
        {canManage && <footer className="flex justify-end border-t border-[var(--line)] px-5 py-4 sm:px-6"><button className="button-primary" disabled={saving}><Save size={16} />{saving ? "Guardando..." : "Guardar configuracion"}</button></footer>}
      </form>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}
