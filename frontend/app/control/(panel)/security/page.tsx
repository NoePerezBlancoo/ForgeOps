"use client";

import { KeyRound, LockKeyhole, ShieldCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { ErrorBanner } from "@/components/feedback";
import { useOperatorAuth } from "@/components/operator-auth-provider";
import { PageHeader } from "@/components/page-header";
import { ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default function OperatorSecurityPage() {
  const { operator, request, logout } = useOperatorAuth();
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (password !== confirm) { setError("Las nuevas contrasenas no coinciden"); return; }
    setSaving(true);
    try {
      await request("/operator-auth/password", { method: "POST", body: JSON.stringify({ current_password: currentPassword, password }) });
      await logout();
      router.replace("/control/login");
    } catch (saveError) {
      setError(saveError instanceof ApiError ? saveError.message : "No se pudo cambiar la contrasena");
    } finally { setSaving(false); }
  }

  return <><PageHeader title="Seguridad del operador" description="Credenciales independientes y segundo factor obligatorio para el control global." /><div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]"><section className="panel p-5"><div className="flex items-center gap-3"><div className="grid size-10 place-items-center rounded-md bg-cyan-50 text-cyan-800"><ShieldCheck size={20} /></div><div><h3 className="text-sm font-bold">Segundo factor activo</h3><p className="mt-1 text-xs text-[var(--muted)]">TOTP requerido en cada nuevo acceso</p></div></div><dl className="mt-6 space-y-4"><SecurityInfo label="Cuenta" value={operator?.email ?? ""} /><SecurityInfo label="Ultimo acceso" value={formatDate(operator?.last_login_at ?? null, true)} /><SecurityInfo label="Duracion maxima" value="8 horas" /><SecurityInfo label="Bloqueo automatico" value="5 intentos fallidos" /></dl><div className="mt-6 flex items-start gap-3 border-l-4 border-l-[var(--accent)] bg-[#f8faf9] p-4"><KeyRound className="mt-0.5 shrink-0 text-[var(--accent)]" size={17} /><p className="text-xs leading-5 text-[var(--muted)]">La clave del autenticador se genera una sola vez durante el bootstrap y se almacena cifrada.</p></div></section><section className="panel overflow-hidden"><header className="border-b border-[var(--line)] px-5 py-4"><div className="flex items-center gap-2"><LockKeyhole size={17} className="text-[var(--accent)]" /><h3 className="text-sm font-bold">Cambiar contrasena</h3></div><p className="mt-1 text-xs text-[var(--muted)]">Al guardarla se cerraran todas las sesiones del operador.</p></header><form onSubmit={submit} className="p-5">{error && <ErrorBanner message={error} />}<div className="space-y-4"><PasswordField label="Contrasena actual" value={currentPassword} onChange={setCurrentPassword} /><PasswordField label="Nueva contrasena" value={password} onChange={setPassword} minLength={10} /><PasswordField label="Confirmar nueva contrasena" value={confirm} onChange={setConfirm} minLength={10} /></div><p className="mt-3 text-[10px] leading-5 text-[var(--muted)]">Minimo 10 caracteres con mayuscula, minuscula y numero. Para el operador recomendamos 14 o mas.</p><div className="mt-5 flex justify-end"><button className="button-primary" disabled={saving}>{saving ? "Actualizando..." : "Actualizar y cerrar sesiones"}</button></div></form></section></div></>;
}

function SecurityInfo({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between gap-4 border-b border-[var(--line)] pb-3 last:border-0"><dt className="text-xs font-semibold text-[var(--muted)]">{label}</dt><dd className="text-right text-xs font-bold">{value}</dd></div>; }
function PasswordField({ label, value, onChange, minLength = 8 }: { label: string; value: string; onChange: (value: string) => void; minLength?: number }) { const current = label === "Contrasena actual"; return <label className="block"><span className="field-label">{label}</span><input className="field mt-2" type="password" value={value} onChange={(event) => onChange(event.target.value)} minLength={minLength} required autoComplete={current ? "current-password" : "new-password"} /></label>; }
