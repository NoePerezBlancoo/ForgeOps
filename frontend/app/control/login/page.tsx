"use client";

import { ArrowLeft, ArrowRight, Gauge, KeyRound, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useOperatorAuth } from "@/components/operator-auth-provider";
import { ApiError } from "@/lib/api";

export default function OperatorLoginPage() {
  const { operator, loading, login } = useOperatorAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && operator) router.replace("/control");
  }, [loading, operator, router]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password, totpCode);
      router.replace("/control");
    } catch (loginError) {
      setError(loginError instanceof ApiError ? loginError.message : "No se pudo validar el acceso");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen bg-[#edf1ef] lg:grid-cols-[minmax(360px,0.8fr)_1.2fr]">
      <section className="relative hidden overflow-hidden bg-[#142021] p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="industrial-grid absolute inset-0 opacity-35" />
        <div className="relative flex items-center gap-3"><div className="grid size-11 place-items-center rounded-md bg-[var(--brand)] text-[var(--brand-ink)]"><Gauge size={25} /></div><div><p className="text-xl font-bold">ForgeOps</p><p className="text-xs font-semibold uppercase text-white/50">Platform Control</p></div></div>
        <div className="relative max-w-md">
          <p className="text-xs font-bold uppercase text-[var(--brand)]">Acceso propietario</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight">Gobierno comercial y operativo de la plataforma.</h1>
          <p className="mt-5 text-sm leading-7 text-white/60">Supervisa empresas, pruebas y suscripciones desde un entorno independiente de los datos industriales de cada cliente.</p>
        </div>
        <div className="relative flex items-center gap-2 text-xs font-semibold text-white/45"><ShieldCheck size={16} /> Acceso protegido con segundo factor y auditoria.</div>
      </section>
      <section className="flex min-h-screen items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden"><div className="grid size-10 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]"><Gauge size={23} /></div><div><p className="text-lg font-bold">ForgeOps Control</p><p className="text-[10px] font-bold uppercase text-[var(--muted)]">Entorno propietario</p></div></div>
          <p className="text-xs font-bold uppercase text-[var(--accent)]">Control de plataforma</p>
          <h2 className="mt-3 text-3xl font-bold">Identificacion reforzada</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Introduce tus credenciales y el codigo actual de tu aplicación autenticadora.</p>
          <form onSubmit={submit} className="mt-8 space-y-5">
            {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{error}</div>}
            <ControlField label="Correo del operador" icon={Mail}><input className="field field-with-icon" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required /></ControlField>
            <ControlField label="Contrasena" icon={LockKeyhole}><input className="field field-with-icon" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" minLength={12} required /></ControlField>
            <ControlField label="Codigo de seis digitos" icon={KeyRound}><input className="field field-with-icon font-mono text-base" value={totpCode} onChange={(event) => setTotpCode(event.target.value.replace(/\D/g, "").slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" pattern="\d{6}" required /></ControlField>
            <button className="button-primary h-11 w-full justify-center" disabled={submitting}>{submitting ? <span className="loader loader-light" /> : <>Acceder al control <ArrowRight size={18} /></>}</button>
          </form>
          <Link href="/login" className="mt-7 inline-flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]"><ArrowLeft size={15} /> Ir al acceso de clientes</Link>
        </div>
      </section>
    </main>
  );
}

function ControlField({ label, icon: Icon, children }: { label: string; icon: typeof Mail; children: React.ReactNode }) {
  return <label className="block"><span className="field-label">{label}</span><div className="relative mt-2"><Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} />{children}</div></label>;
}
