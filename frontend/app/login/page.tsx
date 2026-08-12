"use client";

import { ArrowLeft, ArrowRight, Check, CheckCircle2, Factory, Gauge, LockKeyhole, Mail, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";
import type { TrialRegistration } from "@/lib/types";

type Mode = "login" | "trial";

const emptyTrial: TrialRegistration = {
  company_name: "",
  industry: "",
  plant_name: "",
  full_name: "",
  email: "",
  password: "",
  sample_data: true,
  terms_accepted: false,
};

export default function LoginPage() {
  const { login, registerTrial, user, loading } = useAuth();
  const router = useRouter();
  const demoCredentials = process.env.NEXT_PUBLIC_DEMO_CREDENTIALS !== "false";
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState(demoCredentials ? "admin@metalworks-demo.local" : "");
  const [password, setPassword] = useState(demoCredentials ? "Admin123!" : "");
  const [trial, setTrial] = useState<TrialRegistration>(emptyTrial);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const trialRedirect = useRef(false);

  useEffect(() => {
    if (!loading && user) router.replace(trialRedirect.current ? "/getting-started" : "/dashboard");
  }, [loading, router, user]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    trialRedirect.current = false;
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (loginError) {
      setError(loginError instanceof ApiError ? loginError.message : "No se pudo iniciar sesion");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTrial(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    trialRedirect.current = true;
    try {
      await registerTrial(trial);
      router.replace("/getting-started");
    } catch (registrationError) {
      trialRedirect.current = false;
      setError(registrationError instanceof ApiError ? registrationError.message : "No se pudo iniciar la prueba");
    } finally {
      setSubmitting(false);
    }
  }

  function changeMode(next: Mode) {
    setMode(next);
    setError("");
  }

  return (
    <main className="min-h-screen bg-[#eef1ef] lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden min-h-screen overflow-hidden bg-[#142021] p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="industrial-grid absolute inset-0 opacity-35" />
        <div className="relative flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-md bg-[var(--brand)] text-[var(--brand-ink)]"><Gauge size={25} strokeWidth={2.4} /></div>
          <div><p className="text-xl font-bold">ForgeOps</p><p className="text-xs font-semibold uppercase text-white/50">Industrial CMMS</p></div>
        </div>

        <div className="relative max-w-xl">
          <p className="mb-5 text-xs font-bold uppercase text-[var(--brand)]">Prueba profesional de 30 dias</p>
          <h1 className="text-4xl font-bold leading-tight xl:text-5xl">Mantenimiento industrial claro desde el primer turno.</h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-white/65">Crea tu entorno aislado, trabaja con datos de ejemplo y adapta los modulos al proceso real de tu empresa.</p>
          <div className="mt-10 space-y-4">
            {["Activos, incidencias y ordenes conectados", "Preventivos, repuestos y documentos opcionales", "Tutorial integrado y datos protegidos por empresa"].map((item) => (
              <div key={item} className="flex items-center gap-3 text-sm font-semibold text-white/75"><Check className="text-[var(--brand)]" size={18} /> {item}</div>
            ))}
          </div>
        </div>

        <div className="relative flex items-center gap-2 text-xs font-semibold text-white/45"><ShieldCheck size={16} /> Sin tarjeta. Entorno privado durante 30 dias.</div>
      </section>

      <section className="flex min-h-screen items-center justify-center p-5 sm:p-10">
        <div className={`w-full ${mode === "trial" ? "max-w-xl" : "max-w-md"}`}>
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="grid size-10 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]"><Gauge size={23} /></div>
            <p className="text-xl font-bold">ForgeOps</p>
          </div>

          {mode === "login" ? (
            <>
              <p className="text-xs font-bold uppercase text-[var(--accent)]">Acceso seguro</p>
              <h2 className="mt-3 text-3xl font-bold text-[var(--ink)]">Bienvenido de nuevo</h2>
              <p className="mt-2 text-sm text-[var(--muted)]">Accede al centro de operaciones de tu empresa.</p>
              <form onSubmit={handleLogin} className="mt-8 space-y-5">
                {error && <AuthError message={error} />}
                <InputField label="Correo electronico" icon={Mail}><input className="field field-with-icon" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></InputField>
                <InputField label="Contrasena" icon={LockKeyhole}><input className="field field-with-icon" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" /></InputField>
                <div className="flex justify-end"><Link href="/forgot-password" className="text-xs font-bold text-[var(--accent)]">He olvidado mi contrasena</Link></div>
                <button className="button-primary h-11 w-full justify-center" disabled={submitting}>{submitting ? <span className="loader loader-light" /> : <>Entrar a ForgeOps <ArrowRight size={18} /></>}</button>
              </form>
              <div className="my-6 flex items-center gap-3"><div className="h-px flex-1 bg-[var(--line)]" /><span className="text-[11px] font-bold uppercase text-[var(--muted)]">o prueba tu empresa</span><div className="h-px flex-1 bg-[var(--line)]" /></div>
              <button className="button-secondary h-11 w-full justify-center" onClick={() => changeMode("trial")}><Sparkles size={17} /> Crear prueba de 30 dias</button>
              {demoCredentials && <div className="mt-6 rounded-md border border-[var(--line)] bg-white px-4 py-3"><div className="flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]"><CheckCircle2 size={15} className="text-[var(--success)]" /> Demo guiada disponible</div><p className="mt-1.5 text-xs leading-5 text-[var(--muted)]">Las credenciales completadas permiten revisar el entorno MetalWorks sin crear una cuenta.</p></div>}
            </>
          ) : (
            <>
              <button className="mb-5 inline-flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]" onClick={() => changeMode("login")}><ArrowLeft size={15} /> Volver al acceso</button>
              <p className="text-xs font-bold uppercase text-[var(--accent)]">Prueba profesional</p>
              <h2 className="mt-3 text-3xl font-bold text-[var(--ink)]">Tu entorno en dos minutos</h2>
              <p className="mt-2 text-sm text-[var(--muted)]">30 dias, todos los modulos y datos aislados para tu empresa.</p>
              <form onSubmit={handleTrial} className="mt-7">
                {error && <AuthError message={error} />}
                <div className="grid gap-4 sm:grid-cols-2">
                  <InputField label="Empresa" icon={Factory}><input className="field field-with-icon" value={trial.company_name} onChange={(event) => setTrial({ ...trial, company_name: event.target.value })} minLength={2} required /></InputField>
                  <InputField label="Sector" icon={Factory}><input className="field field-with-icon" value={trial.industry} onChange={(event) => setTrial({ ...trial, industry: event.target.value })} placeholder="Fabricacion, alimentacion..." /></InputField>
                  <InputField label="Planta principal" icon={Factory}><input className="field field-with-icon" value={trial.plant_name} onChange={(event) => setTrial({ ...trial, plant_name: event.target.value })} minLength={2} required /></InputField>
                  <InputField label="Tu nombre" icon={UserRound}><input className="field field-with-icon" value={trial.full_name} onChange={(event) => setTrial({ ...trial, full_name: event.target.value })} minLength={3} required autoComplete="name" /></InputField>
                  <InputField label="Correo profesional" icon={Mail}><input className="field field-with-icon" type="email" value={trial.email} onChange={(event) => setTrial({ ...trial, email: event.target.value })} required autoComplete="email" /></InputField>
                  <InputField label="Contrasena" icon={LockKeyhole}><input className="field field-with-icon" type="password" value={trial.password} onChange={(event) => setTrial({ ...trial, password: event.target.value })} minLength={10} required autoComplete="new-password" /></InputField>
                </div>
                <p className="mt-2 text-[11px] text-[var(--muted)]">Minimo 10 caracteres con mayuscula, minuscula y numero.</p>
                <label className="mt-5 flex items-start gap-3 rounded-md border border-[var(--line)] bg-white p-4"><input type="checkbox" className="mt-0.5 size-4 accent-[var(--accent)]" checked={trial.sample_data} onChange={(event) => setTrial({ ...trial, sample_data: event.target.checked })} /><span><strong className="block text-xs">Incluir datos de ejemplo</strong><span className="mt-1 block text-xs leading-5 text-[var(--muted)]">Tres activos, una incidencia, ordenes, un preventivo y repuestos para aprender trabajando.</span></span></label>
                <label className="mt-4 flex items-start gap-3 text-[11px] leading-5 text-[var(--muted)]"><input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-[var(--accent)]" checked={trial.terms_accepted} onChange={(event) => setTrial({ ...trial, terms_accepted: event.target.checked })} required /><span>Acepto las <a className="font-bold text-[var(--accent)] underline" href="/legal" target="_blank">condiciones de evaluacion y privacidad</a> para la prueba profesional de 30 dias.</span></label>
                <button className="button-primary mt-5 h-11 w-full justify-center" disabled={submitting}>{submitting ? <span className="loader loader-light" /> : <>Crear mi entorno <ArrowRight size={18} /></>}</button>
              </form>
            </>
          )}
        </div>
      </section>
    </main>
  );
}

function InputField({ label, icon: Icon, children }: { label: string; icon: typeof Mail; children: React.ReactNode }) {
  return <label className="block"><span className="field-label">{label}</span><div className="relative mt-2"><Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} />{children}</div></label>;
}

function AuthError({ message }: { message: string }) {
  return <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{message}</div>;
}
