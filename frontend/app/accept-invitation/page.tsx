"use client";

import { ArrowLeft, CheckCircle2, Gauge, LockKeyhole, ShieldCheck, UserCheck } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";
import { formatDate, labelFor } from "@/lib/format";
import type { UserRole } from "@/lib/types";

interface InvitationPreview {
  company_name: string;
  email: string;
  full_name: string;
  role: UserRole;
  expires_at: string;
}

function InvitationForm() {
  const token = useSearchParams().get("token") ?? "";
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setError("El enlace de invitacion no es valido");
      setLoading(false);
      return;
    }
    apiRequest<InvitationPreview>("/invitations/preview", {
      method: "POST",
      body: JSON.stringify({ token }),
    }).then(setPreview).catch((requestError) => {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo validar la invitacion");
    }).finally(() => setLoading(false));
  }, [token]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== confirmation) {
      setError("Las contrasenas no coinciden");
      return;
    }
    setSubmitting(true);
    try {
      await apiRequest("/invitations/accept", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      setCompleted(true);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo activar la cuenta");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] p-5">
      <section className="w-full max-w-lg">
        <div className="mb-8 flex items-center gap-3"><div className="grid size-10 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]"><Gauge size={23} /></div><div><p className="text-xl font-bold">ForgeOps</p><p className="text-[10px] font-bold uppercase text-[var(--muted)]">Industrial CMMS</p></div></div>
        {loading ? <div className="panel grid h-56 place-items-center"><span className="loader" /></div> : completed ? (
          <div className="panel p-7 text-center"><CheckCircle2 className="mx-auto text-[var(--success)]" size={40} /><h1 className="mt-4 text-2xl font-bold">Cuenta activada</h1><p className="mt-2 text-sm leading-6 text-[var(--muted)]">Tu acceso ya esta preparado. Puedes entrar en el espacio de mantenimiento de tu empresa.</p><Link href="/login" className="button-primary mt-6 h-11 justify-center">Iniciar sesion</Link></div>
        ) : preview ? (
          <div className="panel overflow-hidden">
            <header className="border-b border-[var(--line)] bg-[#142021] px-6 py-5 text-white"><div className="flex items-center gap-3"><UserCheck className="text-[var(--brand)]" size={24} /><div><p className="text-[11px] font-bold uppercase text-white/50">Invitacion de empresa</p><h1 className="mt-1 text-xl font-bold">Activa tu acceso</h1></div></div></header>
            <div className="p-6"><p className="text-sm leading-6 text-[var(--muted)]"><strong className="text-[var(--ink)]">{preview.company_name}</strong> te ha invitado a trabajar en ForgeOps.</p><dl className="mt-5 grid gap-3 rounded-md border border-[var(--line)] bg-slate-50 p-4 sm:grid-cols-2"><div><dt className="text-[10px] font-bold uppercase text-[var(--muted)]">Persona</dt><dd className="mt-1 text-sm font-bold">{preview.full_name}</dd></div><div><dt className="text-[10px] font-bold uppercase text-[var(--muted)]">Rol</dt><dd className="mt-1 text-sm font-bold">{labelFor(preview.role)}</dd></div><div className="sm:col-span-2"><dt className="text-[10px] font-bold uppercase text-[var(--muted)]">Correo</dt><dd className="mt-1 break-all text-sm font-semibold">{preview.email}</dd></div></dl><form onSubmit={submit} className="mt-5 space-y-4">{error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{error}</div>}<PasswordField label="Crea tu contrasena" value={password} onChange={setPassword} /><PasswordField label="Confirma tu contrasena" value={confirmation} onChange={setConfirmation} /><p className="text-[11px] leading-5 text-[var(--muted)]">Minimo 10 caracteres con mayuscula, minuscula y numero. Invitacion valida hasta {formatDate(preview.expires_at, true)}.</p><button className="button-primary h-11 w-full justify-center" disabled={submitting}>{submitting ? "Activando..." : <><ShieldCheck size={17} /> Activar cuenta</>}</button></form></div>
          </div>
        ) : (
          <div className="panel p-7 text-center"><ShieldCheck className="mx-auto text-red-700" size={36} /><h1 className="mt-4 text-xl font-bold">Invitacion no disponible</h1><p className="mt-2 text-sm leading-6 text-[var(--muted)]">{error || "El enlace ha caducado, ya se utilizo o fue revocado."}</p><Link href="/login" className="button-secondary mt-6"><ArrowLeft size={16} /> Volver al acceso</Link></div>
        )}
      </section>
    </main>
  );
}

export default function AcceptInvitationPage() {
  return <Suspense><InvitationForm /></Suspense>;
}

function PasswordField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block"><span className="field-label">{label}</span><div className="relative mt-2"><LockKeyhole className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} /><input className="field field-with-icon" type="password" value={value} onChange={(event) => onChange(event.target.value)} minLength={10} required autoComplete="new-password" /></div></label>;
}
