"use client";

import { ArrowLeft, CheckCircle2, Gauge, Mail } from "lucide-react";
import Link from "next/link";
import { FormEvent, useState } from "react";

import { ApiError, apiRequest } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await apiRequest("/auth/password-reset/request", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo procesar la solicitud");
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
        {sent ? (
          <div className="panel p-6 text-center">
            <CheckCircle2 className="mx-auto text-[var(--success)]" size={36} />
            <h1 className="mt-4 text-xl font-bold">Revisa tu correo</h1>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">Si existe una cuenta con esa direccion, recibiras un enlace valido durante 30 minutos.</p>
          </div>
        ) : (
          <>
            <p className="text-xs font-bold uppercase text-[var(--accent)]">Recuperacion segura</p>
            <h1 className="mt-3 text-3xl font-bold">Recupera tu acceso</h1>
            <p className="mt-2 text-sm text-[var(--muted)]">Enviaremos un enlace de un solo uso a tu correo profesional.</p>
            <form onSubmit={submit} className="mt-7 space-y-5">
              {error && <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">{error}</div>}
              <label className="block"><span className="field-label">Correo electronico</span><div className="relative mt-2"><Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={18} /><input className="field field-with-icon" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoComplete="email" /></div></label>
              <button className="button-primary h-11 w-full justify-center" disabled={submitting}>{submitting ? "Enviando..." : "Enviar enlace seguro"}</button>
            </form>
          </>
        )}
        <Link href="/login" className="mt-6 inline-flex items-center gap-2 text-xs font-bold text-[var(--ink-soft)]"><ArrowLeft size={15} /> Volver al acceso</Link>
      </section>
    </main>
  );
}
