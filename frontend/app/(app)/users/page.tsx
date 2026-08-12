"use client";

import { KeyRound, Pencil, Search, ShieldCheck, UserPlus, Users } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorBanner, LoadingBlock } from "@/components/feedback";
import { Modal } from "@/components/modal";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ApiError } from "@/lib/api";
import { formatDate, initials } from "@/lib/format";
import type { User, UserRole } from "@/lib/types";

interface UserForm {
  full_name: string;
  email: string;
  job_title: string;
  phone: string;
  role: UserRole;
  active: boolean;
  password: string;
}

const emptyForm: UserForm = { full_name: "", email: "", job_title: "", phone: "", role: "TECHNICIAN", active: true, password: "" };

export default function UsersPage() {
  const { request, user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [form, setForm] = useState<UserForm>(emptyForm);
  const [newPassword, setNewPassword] = useState("");
  const canManage = currentUser && ["SUPER_ADMIN", "ADMIN"].includes(currentUser.role);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setUsers(await request<User[]>(`/users?active_only=${canManage ? "false" : "true"}`));
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo cargar el equipo");
    } finally {
      setLoading(false);
    }
  }, [canManage, request]);

  useEffect(() => {
    void loadUsers();
  }, [loadUsers]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return users.filter((member) => {
      const matchesSearch = !term || [member.full_name, member.email, member.job_title].filter(Boolean).some((value) => value!.toLowerCase().includes(term));
      const matchesRole = !roleFilter || member.role === roleFilter;
      const matchesStatus = statusFilter === "all" || (statusFilter === "active" ? member.active : !member.active);
      return matchesSearch && matchesRole && matchesStatus;
    });
  }, [roleFilter, search, statusFilter, users]);

  const activeUsers = users.filter((member) => member.active).length;
  const administrators = users.filter((member) => member.active && ["SUPER_ADMIN", "ADMIN"].includes(member.role)).length;

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setModalOpen(true);
  }

  function openEdit(member: User) {
    setEditing(member);
    setForm({ full_name: member.full_name, email: member.email, job_title: member.job_title ?? "", phone: member.phone ?? "", role: member.role, active: member.active, password: "" });
    setModalOpen(true);
  }

  async function saveUser(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const basePayload = { full_name: form.full_name, email: form.email, job_title: form.job_title || null, phone: form.phone || null, role: form.role, active: form.active };
      await request(editing ? `/users/${editing.id}` : "/users", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(editing ? basePayload : { ...basePayload, active: undefined, password: form.password }),
      });
      setModalOpen(false);
      setNotice(editing ? "Usuario actualizado" : "Usuario creado");
      await loadUsers();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo guardar el usuario");
    } finally {
      setSaving(false);
    }
  }

  function openPassword(member: User) {
    setEditing(member);
    setNewPassword("");
    setPasswordOpen(true);
  }

  async function resetPassword(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await request(`/users/${editing.id}/password`, { method: "POST", body: JSON.stringify({ password: newPassword }) });
      setPasswordOpen(false);
      setNotice(`Contrasena restablecida para ${editing.full_name}`);
      await loadUsers();
    } catch (requestError) {
      setError(requestError instanceof ApiError ? requestError.message : "No se pudo restablecer la contrasena");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Equipo y permisos" description="Personas con acceso a la empresa, responsabilidades y nivel de autorizacion." actions={canManage ? <button className="button-primary" onClick={openCreate}><UserPlus size={17} /> Nuevo usuario</button> : undefined} />
      {error && <ErrorBanner message={error} />}
      {notice && <div className="notice-success">{notice}</div>}
      <section className="mb-4 grid gap-3 sm:grid-cols-3">
        <article className="panel flex items-center gap-3 p-4"><div className="grid size-9 place-items-center rounded-md bg-cyan-50 text-cyan-800"><Users size={18} /></div><div><p className="text-xl font-bold">{activeUsers}</p><p className="text-[11px] font-semibold text-[var(--muted)]">Usuarios activos</p></div></article>
        <article className="panel flex items-center gap-3 p-4"><div className="grid size-9 place-items-center rounded-md bg-emerald-50 text-emerald-700"><ShieldCheck size={18} /></div><div><p className="text-xl font-bold">{administrators}</p><p className="text-[11px] font-semibold text-[var(--muted)]">Administradores</p></div></article>
        <article className="panel flex items-center gap-3 p-4"><div className="grid size-9 place-items-center rounded-md bg-slate-100 text-slate-700"><Users size={18} /></div><div><p className="text-xl font-bold">{users.length - activeUsers}</p><p className="text-[11px] font-semibold text-[var(--muted)]">Accesos inactivos</p></div></article>
      </section>
      <section className="panel mb-4 grid gap-3 p-3 md:grid-cols-[1fr_220px_180px]">
        <label className="relative"><Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" size={17} /><input className="field field-with-icon" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar por nombre, correo o puesto" /></label>
        <select className="field" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}><option value="">Todos los roles</option><option value="ADMIN">Administradores</option><option value="MAINTENANCE_MANAGER">Responsables</option><option value="TECHNICIAN">Tecnicos</option><option value="VIEWER">Consulta</option></select>
        <select className="field" value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}><option value="active">Activos</option><option value="inactive">Inactivos</option><option value="all">Todos</option></select>
      </section>
      {loading ? <LoadingBlock /> : (
        <section className="panel overflow-hidden">
          {filtered.length === 0 ? <EmptyState title="No hay usuarios coincidentes" detail="Ajusta los filtros o crea un nuevo acceso." /> : <div className="table-wrap"><table className="data-table"><thead><tr><th>Persona</th><th>Puesto</th><th>Rol</th><th>Ultimo acceso</th><th>Estado</th><th className="w-28">Acciones</th></tr></thead><tbody>{filtered.map((member) => <tr key={member.id}><td><div className="flex items-center gap-3"><div className="grid size-9 shrink-0 place-items-center rounded-md bg-[var(--ink)] text-[11px] font-bold text-white">{initials(member.full_name)}</div><div><p className="font-bold text-[var(--ink)]">{member.full_name}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{member.email}</p></div></div></td><td><p className="font-semibold text-[var(--ink-soft)]">{member.job_title ?? "Sin puesto definido"}</p><p className="mt-1 text-[11px] text-[var(--muted)]">{member.phone ?? "Sin telefono"}</p></td><td><StatusBadge value={member.role} /></td><td>{member.last_login_at ? formatDate(member.last_login_at, true) : "Nunca"}</td><td><StatusBadge value={member.active ? "ACTIVE" : "OUT_OF_SERVICE"} /></td><td>{canManage && <div className="flex gap-2"><button className="icon-button" onClick={() => openEdit(member)} aria-label={`Editar ${member.full_name}`}><Pencil size={16} /></button><button className="icon-button" onClick={() => openPassword(member)} aria-label={`Restablecer contrasena de ${member.full_name}`}><KeyRound size={16} /></button></div>}</td></tr>)}</tbody></table></div>}
        </section>
      )}
      <Modal open={modalOpen} title={editing ? `Editar ${editing.full_name}` : "Nuevo usuario"} description="Acceso, responsabilidad y permisos dentro de la empresa." onClose={() => setModalOpen(false)}>
        <form onSubmit={saveUser}><div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6"><Field label="Nombre completo"><input className="field" value={form.full_name} onChange={(event) => setForm({ ...form, full_name: event.target.value })} required /></Field><Field label="Correo"><input className="field" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required /></Field><Field label="Puesto"><input className="field" value={form.job_title} onChange={(event) => setForm({ ...form, job_title: event.target.value })} placeholder="Tecnico electromecanico" /></Field><Field label="Telefono"><input className="field" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></Field><Field label="Rol"><select className="field" value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as UserRole })}>{currentUser?.role === "SUPER_ADMIN" && <option value="SUPER_ADMIN">Superadministrador</option>}<option value="ADMIN">Administrador</option><option value="MAINTENANCE_MANAGER">Responsable de mantenimiento</option><option value="TECHNICIAN">Tecnico</option><option value="VIEWER">Solo consulta</option></select></Field>{!editing && <Field label="Contrasena temporal"><input className="field" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} minLength={10} required /><span className="mt-1 block text-[10px] text-[var(--muted)]">Minimo 10 caracteres, mayuscula, minuscula y numero.</span></Field>}{editing && <label className="flex items-center gap-3 rounded-md border border-[var(--line)] bg-[#fafcfb] px-4 py-3"><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /><span><strong className="block text-xs">Acceso activo</strong><span className="text-[10px] text-[var(--muted)]">Al desactivar se cierran sus sesiones.</span></span></label>}</div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button type="button" className="button-secondary" onClick={() => setModalOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}>{saving ? "Guardando..." : editing ? "Guardar cambios" : "Crear usuario"}</button></footer></form>
      </Modal>
      <Modal open={passwordOpen} title="Restablecer contrasena" description={editing ? `Se cerraran las sesiones activas de ${editing.full_name}.` : undefined} onClose={() => setPasswordOpen(false)}><form onSubmit={resetPassword}><div className="p-5 sm:p-6"><Field label="Nueva contrasena temporal"><input className="field" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={10} required /><span className="mt-2 block text-xs text-[var(--muted)]">Debe incluir mayuscula, minuscula y numero.</span></Field></div><footer className="flex justify-end gap-2 border-t border-[var(--line)] px-5 py-4"><button type="button" className="button-secondary" onClick={() => setPasswordOpen(false)}>Cancelar</button><button className="button-primary" disabled={saving}><KeyRound size={16} /> Restablecer</button></footer></form></Modal>
    </>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block"><span className="field-label mb-2">{label}</span>{children}</label>;
}
