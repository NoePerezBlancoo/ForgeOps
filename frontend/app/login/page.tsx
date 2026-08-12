"use client";

import { ArrowRight, CheckCircle2, Gauge, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("admin@metalworks-demo.local");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, router, user]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (loginError) {
      setError(loginError instanceof ApiError ? loginError.message : "No se pudo iniciar sesion");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#eef1ef] lg:grid lg:grid-cols-[1.1fr_0.9fr]">
      <section className="relative hidden min-h-screen overflow-hidden bg-[#142021] p-12 text-white lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="industrial-grid absolute inset-0 opacity-35" />
        <div className="relative flex items-center gap-3">
          <div className="grid size-11 place-items-center rounded-md bg-[var(--brand)] text-[var(--brand-ink)]">
            <Gauge size={25} strokeWidth={2.4} />
          </div>
          <div>
            <p className="text-xl font-bold">ForgeOps</p>
            <p className="text-xs font-semibold uppercase text-white/50">Industrial CMMS</p>
          </div>
        </div>

        <div className="relative max-w-xl">
          <p className="mb-5 text-xs font-bold uppercase text-[var(--brand)]">MetalWorks Demo S.L.</p>
          <h1 className="text-4xl font-bold leading-tight xl:text-5xl">
            La operacion de mantenimiento, bajo control.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-white/65">
            Activos, averias y trabajo de planta en una unica vista operativa, preparada para equipos industriales reales.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4">
            {[
              ["10", "Activos"],
              ["8", "Incidencias"],
              ["15", "Ordenes"],
            ].map(([value, label]) => (
              <div key={label} className="border-l-2 border-[var(--brand)] pl-4">
                <p className="text-2xl font-bold">{value}</p>
                <p className="mt-1 text-xs font-semibold text-white/45">{label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative flex items-center gap-2 text-xs font-semibold text-white/45">
          <ShieldCheck size={16} /> Aislamiento multiempresa y control de permisos
        </div>
      </section>

      <section className="flex min-h-screen items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-md">
          <div className="mb-10 flex items-center gap-3 lg:hidden">
            <div className="grid size-10 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]">
              <Gauge size={23} />
            </div>
            <p className="text-xl font-bold">ForgeOps</p>
          </div>
          <p className="text-xs font-bold uppercase text-[var(--accent)]">Acceso seguro</p>
          <h2 className="mt-3 text-3xl font-bold text-[var(--ink)]">Bienvenido de nuevo</h2>
          <p className="mt-2 text-sm text-[var(--muted)]">Accede al centro de operaciones de tu planta.</p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{error}</div>}
            <label className="block">
              <span className="field-label">Correo electronico</span>
              <div className="relative mt-2">
                <Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} />
                <input className="field field-with-icon" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" />
              </div>
            </label>
            <label className="block">
              <span className="field-label">Contrasena</span>
              <div className="relative mt-2">
                <LockKeyhole className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} />
                <input className="field field-with-icon" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
              </div>
            </label>
            <button className="button-primary h-11 w-full justify-center" disabled={submitting}>
              {submitting ? <span className="loader loader-light" /> : <>Entrar a ForgeOps <ArrowRight size={18} /></>}
            </button>
          </form>

          <div className="mt-7 rounded-md border border-[var(--line)] bg-white px-4 py-3">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]">
              <CheckCircle2 size={15} className="text-[var(--success)]" /> Entorno demostracion preparado
            </div>
            <p className="mt-1.5 text-xs leading-5 text-[var(--muted)]">Las credenciales de acceso ya estan completadas para revisar la plataforma.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
