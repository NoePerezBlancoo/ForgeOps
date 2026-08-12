"use client";

import { ArrowLeft, CheckCircle2, Gauge, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("El enlace de recuperacion no es valido");
      return;
    }
    if (password !== confirmation) {
      setError("Las contrasenas no coinciden");
      return;
    }
    setSubmitting(true);
    try {
      await apiRequest("/auth/password-reset/confirm", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      setCompleted(true);
    } catch (resetError) {
      setError(resetError instanceof ApiError ? resetError.message : "No se pudo actualizar la contrasena");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[var(--canvas)] p-5">
      <section className="w-full max-w-md">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]"><Gauge size={23} /></div>
          <p className="text-xl font-bold">ForgeOps</p>
        </div>
        {completed ? (
          <div className="panel p-6 text-center">
            <CheckCircle2 className="mx-auto text-[var(--success)]" size={36} />
            <h1 className="mt-4 text-xl font-bold">Acceso recuperado</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">La contrasena se ha actualizado y las sesiones renovables anteriores se han cerrado.</p>
            <Link href="/login" className="button-primary mt-6 h-11 justify-center">Iniciar sesion</Link>
          </div>
        ) : (
          <>
            <p className="text-xs font-bold uppercase text-[var(--accent)]">Recuperacion segura</p>
            <h1 className="mt-3 text-3xl font-bold">Nueva contrasena</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">El enlace es de un solo uso y caduca en 30 minutos.</p>
            <form onSubmit={submit} className="mt-7 space-y-4">
              {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{error}</div>}
              <PasswordField label="Nueva contrasena" value={password} onChange={setPassword} />
              <PasswordField label="Confirmar contrasena" value={confirmation} onChange={setConfirmation} />
              <button className="button-primary h-11 w-full justify-center" disabled={submitting}>{submitting ? "Actualizando..." : "Actualizar contrasena"}</button>
            </form>
            <Link href="/login" className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]"><ArrowLeft size={15} /> Volver al acceso</Link>
          </>
        )}
      </section>
    </main>
  );
}

export default function ResetPasswordPage() {
  return <Suspense><ResetPasswordForm /></Suspense>;
}

function PasswordField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return <label className="block"><span className="field-label">{label}</span><div className="relative mt-2"><LockKeyhole className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} /><input className="field field-with-icon" type="password" value={value} onChange={(event) => onChange(event.target.value)} minLength={10} required autoComplete="new-password" /></div></label>;
}
