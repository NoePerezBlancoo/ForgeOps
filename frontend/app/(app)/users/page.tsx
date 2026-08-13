"use client";

import { Ban, KeyRound, MailPlus, Pencil, RefreshCw, Search, Send, ShieldCheck, UserCheck, Users } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, initials } from "@/lib/format";
import type { User, UserInvitation, UserInvitationList, UserRole } from "@/lib/types";

interface UserForm {
  full_name: string;
  email: string;
  job_title: string;
  phone: string;
  role: UserRole;
  active: boolean;
}

const emptyForm: UserForm = { full_name: "", email: "", job_title: "", phone: "", role: "TECHNICIAN", active: true };

export default function UsersPage() {
  const { request, user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [pendingInvitations, setPendingInvitations] = useState(0);
  const [view, setView] = useState<"team" | "invitations">("team");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [revokingInvitation, setRevokingInvitation] = useState<UserInvitation | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<UserForm>(emptyForm);
  const [newPassword, setNewPassword] = useState("");
  const canManage = Boolean(currentUser && ["SUPER_ADMIN", "ADMIN"].includes(currentUser.role));

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [team, invitationData] = await Promise.all([
        request<User[]>("/users?active_only=false"),
        request<UserInvitationList>("/invitations"),
      ]);
      setUsers(team);
      setInvitations(invitationData.items);
      setPendingInvitations(invitationData.pending);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el equipo");
    } finally {
      setLoading(false);
    }
  }, [request]);

  useEffect(() => { void loadData(); }, [loadData]);

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase();
    return users.filter((member) => {
      const matchesSearch = !term || [member.full_name, member.email, member.job_title].filter(Boolean).some((value) => value!.toLowerCase().includes(term));
      const matchesRole = !roleFilter || member.role === roleFilter;
      const matchesStatus = statusFilter === "all" || (statusFilter === "active" ? member.active : !member.active);
      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [roleFilter, search, statusFilter, users]);

  const filteredInvitations = useMemo(() => {
    const term = search.trim().toLowerCase();
    return invitations.filter((invitation) => !term || [invitation.full_name, invitation.email, invitation.job_title].filter(Boolean).some((value) => value!.toLowerCase().includes(term)));
  }, [invitations, search]);

  const activeUsers = users.filter((member) => member.active).length;
  const administrators = users.filter((member) => member.active && ["SUPER_ADMIN", "ADMIN"].includes(member.role)).length;

  function openInvite() {
    setError("");
    setNotice("");
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(member: User) {
    setError("");
    setNotice("");
    setEditing(member);
    setForm({ full_name: member.full_name, email: member.email, job_title: member.job_title ?? "", phone: member.phone ?? "", role: member.role, active: member.active });
    setModalOpen(true);
  }

  async function saveMember(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = { full_name: form.full_name, email: form.email, job_title: form.job_title || null, phone: form.phone || null, role: form.role };
      if (editing) {
        await request(`/users/${editing.id}`, { method: "PATCH", body: JSON.stringify({ ...payload, active: form.active }) });
        setNotice("Usuario actualizado");
      } else {
        await request("/invitations", { method: "POST", body: JSON.stringify(payload) });
        setNotice(`Invitacion enviada a ${form.email}`);
        setView("invitations");
      }
      setModalOpen(false);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar el acceso");
    } finally {
      setSaving(false);
    }
  }

  function openPassword(member: User) {
    setError("");
    setNotice("");
    setEditing(member);
    setNewPassword("");
    setPasswordOpen(true);
  }

  async function resetPassword(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    setError("");
    try {
      await request(`/users/${editing.id}/password`, { method: "POST", body: JSON.stringify({ password: newPassword }) });
      setPasswordOpen(false);
      setNotice(`Contrasena restablecida para ${editing.full_name}`);
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo restablecer la contrasena");
    } finally {
      setSaving(false);
    }
  }

  async function resendInvitation(invitation: UserInvitation) {
    setSaving(true);
    setError("");
    try {
      await request(`/invitations/${invitation.id}/resend`, { method: "POST" });
      setNotice(`Invitacion reenviada a ${invitation.email}`);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo reenviar la invitacion");
    } finally {
      setSaving(false);
    }
  }

  async function revokeInvitation(invitation: UserInvitation) {
    setSaving(true);
    setError("");
    try {
      await request(`/invitations/${invitation.id}/revoke`, { method: "POST" });
      setNotice("Invitacion revocada");
      setRevokingInvitation(null);
      await loadData();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo revocar la invitacion");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Equipo y permisos" description="Accesos, responsabilidades e invitaciones de la empresa." actions={canManage ? <button className="button-primary" onClick={openInvite}><MailPlus size={17} /> Invitar persona</button> : undefined} />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Users} value={activeUsers} label="Usuarios activos" tone="bg-cyan-50 text-cyan-800" />
        <Metric icon={ShieldCheck} value={administrators} label="Administradores" tone="bg-emerald-50 text-emerald-700" />
        <Metric icon={Send} value={pendingInvitations} label="Invitaciones pendientes" tone="bg-amber-50 text-amber-800" />
        <Metric icon={UserCheck} value={users.length - activeUsers} label="Accesos inactivos" tone="bg-slate-100 text-slate-700" />
      </section>
      <section className="panel mb-4 p-3">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[auto_minmax(180px,1fr)_220px_180px] xl:items-center">
          <div className="inline-flex self-start rounded-md border border-[var(--line)] bg-slate-50 p-1">
            <button className={`h-8 rounded px-3 text-xs font-bold ${view === "team" ? "bg-white text-[var(--ink)] shadow-sm" : "text-[var(--muted)]"}`} onClick={() => setView("team")}>Equipo</button>
            <button className={`h-8 rounded px-3 text-xs font-bold ${view === "invitations" ? "bg-white text-[var(--ink)] shadow-sm" : "text-[var(--muted)]"}`} onClick={() => setView("invitations")}>Invitaciones {pendingInvitations > 0 && `(${pendingInvitations})`}</button>
          </div>
          <label className={`relative min-w-0 ${view === "invitations" ? "xl:col-span-3" : ""}`}><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre, correo o puesto" /></label>
          {view === "team" && <><select className="field" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}><option value="">Todos los roles</option><option value="ADMIN">Administradores</option><option value="MAINTENANCE_MANAGER">Responsables</option><option value="TECHNICIAN">Tecnicos</option><option value="VIEWER">Consulta</option></select><select className="field" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="active">Activos</option><option value="inactive">Inactivos</option><option value="all">Todos</option></select></>}
        </div>
      </section>
      {loading ? <LoadingBlock /> : view === "team" ? <TeamTable users={filteredUsers} canManage={canManage} onEdit={openEdit} onPassword={openPassword} /> : <InvitationTable invitations={filteredInvitations} saving={saving} onResend={resendInvitation} onRevoke={setRevokingInvitation} />}
      <Modal open={modalOpen} title={editing ? `Editar ${editing.full_name}` : "Invitar persona"} description={editing ? "Actualiza su responsabilidad y nivel de acceso." : "La persona recibira un enlace seguro para crear su contrasena."} onClose={() => setModalOpen(false)}>
        <form onSubmit={saveMember}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6">{error && <div className="sm:col-span-2"><ErrorBanner message={error} /></div>}<Field label="Nombre completo"><input className="field" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} minLength={3} required /></Field><Field label="Correo"><input className="field" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></Field><Field label="Puesto"><input className="field" value={form.job_title} onChange={(event) => setForm({ ...form, job_title: event.target.value })} placeholder="Tecnico electromecanico" /></Field><Field label="Telefono"><input className="field" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field><Field label="Rol"><select className="field" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}>{currentUser?.role === "SUPER_ADMIN" && <option value="SUPER_ADMIN">Superadministrador</option>}<option value="ADMIN">Administrador</option><option value="MAINTENANCE_MANAGER">Responsable de mantenimiento</option><option value="TECHNICIAN">Tecnico</option><option value="VIEWER">Solo consulta</option></select></Field>{editing && <label className="flex items-center gap-3 rounded-md border border-[var(--line)] bg-[#fafcfb] px-4 py-3"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /><span><strong className="block text-xs">Acceso activo</strong><span className="text-[10px] text-[var(--muted)]">Al desactivar se cierran sus sesiones.</span></span></label>}</div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? "Guardando..." : editing ? "Guardar cambios" : <><Send size={16} /> Enviar invitacion</>}</button></footer></form>
      </Modal>
      <Modal open={passwordOpen} title="Restablecer contrasena" description={editing ? `Se cerraran las sesiones activas de ${editing.full_name}.` : undefined} onClose={() => setPasswordOpen(false)}><form onSubmit={resetPassword}><div className="space-y-4 p-5 sm:p-6">{error && <ErrorBanner message={error} />}<Field label="Nueva contrasena temporal"><input className="field" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={10} required /><span className="mt-2 block text-xs text-[var(--muted)]">Debe incluir mayuscula, minuscula y numero.</span></Field></div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button type="button" className="button-secondary" onClick={() => setPasswordOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}><KeyRound size={16} /> Restablecer</button></footer></form></Modal>
      <Modal open={Boolean(revokingInvitation)} title="Revocar invitacion" description={revokingInvitation ? `${revokingInvitation.full_name} ya no podra utilizar el enlace enviado.` : undefined} onClose={() => setRevokingInvitation(null)}><div className="p-5 sm:p-6"><p className="text-sm leading-6 text-[var(--muted)]">El registro se conservara como parte del historial de accesos de la empresa.</p></div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button className="button-secondary" onClick={() => setRevokingInvitation(null)}>Cancelar</button><button className="button-danger" disabled={saving} onClick={() => revokingInvitation && void revokeInvitation(revokingInvitation)}><Ban size={16} /> {saving ? "Revocando..." : "Revocar invitacion"}</button></footer></Modal>
    </>
  );
}

function TeamTable({ users, canManage, onEdit, onPassword }: { users: User[]; canManage: boolean; onEdit: (member: User) => void; onPassword: (member: User) => void }) {
  return <section className="panel overflow-hidden">{users.length === 0 ? <EmptyState title="No hay usuarios coincidentes" detail="Ajusta los filtros o invita a una nueva persona." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Persona</th><th>Puesto</th><th>Rol</th><th>Ultimo acceso</th><th>Estado</th><th className="w-28">Acciones</th></tr></thead><tbody>{users.map((member) => <tr key={member.id}><td><div className="flex items-center gap-3"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-[var(--ink)] text-[11px] font-bold text-white">{initials(member.full_name)}</div><div><p className="font-bold text-[var(--ink)]">{member.full_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{member.email}</p></div></div></td><td><p className="font-semibold text-[var(--ink-soft)]">{member.job_title ?? "Sin puesto definido"}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{member.phone ?? "Sin telefono"}</p></td><td><StatusBadge value={member.role} /></td><td>{member.last_login_at ? formatDate(member.last_login_at, true) : "Nunca"}</td><td><StatusBadge value={member.active ? "ACTIVE" : "OUT_OF_SERVICE"} /></td><td>{canManage && <div className="flex gap-2"><button className="icon-button" onClick={() => onEdit(member)} aria-label={`Editar ${member.full_name}`} title="Editar"><Pencil size={16} /></button><button className="icon-button" onClick={() => onPassword(member)} aria-label={`Restablecer contrasena de ${member.full_name}`} title="Restablecer contrasena"><KeyRound size={16} /></button></div>}</td></tr>)}</tbody></table></div>}</section>;
}

function InvitationTable({ invitations, saving, onResend, onRevoke }: { invitations: UserInvitation[]; saving: boolean; onResend: (invitation: UserInvitation) => void; onRevoke: (invitation: UserInvitation) => void }) {
  return <section className="panel overflow-hidden">{invitations.length === 0 ? <EmptyState title="No hay invitaciones" detail="Invita a tu equipo para que cada intervencion quede asociada a la persona correcta." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Persona invitada</th><th>Rol</th><th>Enviada</th><th>Caducidad</th><th>Estado</th><th className="w-28">Acciones</th></tr></thead><tbody>{invitations.map((invitation) => <tr key={invitation.id}><td><p className="font-bold text-[var(--ink)]">{invitation.full_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{invitation.email}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{invitation.job_title ?? "Sin puesto definido"}</p></td><td><StatusBadge value={invitation.role} /></td><td>{formatDate(invitation.created_at, true)}</td><td>{formatDate(invitation.expires_at, true)}</td><td><StatusBadge value={invitation.status} /></td><td>{invitation.status !== "ACCEPTED" && <div className="flex gap-2"><button className="icon-button" disabled={saving} onClick={() => void onResend(invitation)} aria-label={`Reenviar invitacion a ${invitation.full_name}`} title="Reenviar"><RefreshCw size={16} /></button>{invitation.status === "PENDING" && <button className="icon-button text-red-700" disabled={saving} onClick={() => void onRevoke(invitation)} aria-label={`Revocar invitacion de ${invitation.full_name}`} title="Revocar"><Ban size={16} /></button>}</div>}</td></tr>)}</tbody></table></div>}</section>;
}

function Metric({ icon: Icon, value, label, tone }: { icon: typeof Users; value: number; label: string; tone: string }) {
  return <article className="panel flex items-center gap-3 p-4"><div className={`grid size-9 place-items-center rounded-md ${tone}`}><Icon size={18} /></div><div><p className="text-xl font-bold">{value}</p><p className="text-[11px] font-semibold text-[var(--muted)]">{label}</p></div></article>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}
