"use client";

import {
  Boxes,
  BrainCircuit,
  Building2,
  CircleHelp,
  ClipboardList,
  Factory,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  ShieldCheck,
  ShieldAlert,
  SlidersHorizontal,
  Users,
  Wrench,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { AccessBlocked, ModuleUnavailable, TrialBanner } from "@/components/commercial-state";
import { HelpDrawer } from "@/components/help-drawer";
import { useWorkspace } from "@/components/workspace-provider";
import { initials, labelFor } from "@/lib/format";
import { moduleForPath } from "@/lib/modules";

const primaryNavigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/work-orders", label: "Ordenes de trabajo", icon: ClipboardList },
  { href: "/incidents", label: "Incidencias", icon: ShieldAlert },
  { href: "/assets", label: "Activos", icon: Boxes },
];

const planningNavigation = [
  { href: "/preventive-maintenance", label: "Preventivos", icon: Wrench, module: "PREVENTIVE" as const },
  { href: "/inventory", label: "Inventario", icon: PackageSearch, module: "INVENTORY" as const },
  { href: "/documents", label: "Documentos", icon: FileText, module: "DOCUMENTS" as const },
];

const intelligenceNavigation = [
  { href: "/knowledge", label: "Asistente documental", icon: BrainCircuit, module: "KNOWLEDGE" as const },
];

const administrationNavigation = [
  { href: "/company", label: "Empresa", icon: Building2 },
  { href: "/plants", label: "Plantas", icon: Factory },
  { href: "/users", label: "Usuarios", icon: Users, adminOnly: true },
  { href: "/modules", label: "Modulos", icon: SlidersHorizontal, adminOnly: true },
];

const pageNames: Record<string, string> = {
  "/dashboard": "Vision general",
  "/assets": "Activos industriales",
  "/incidents": "Gestion de incidencias",
  "/work-orders": "Ordenes de trabajo",
  "/preventive-maintenance": "Mantenimiento preventivo",
  "/inventory": "Inventario de repuestos",
  "/documents": "Documentacion tecnica",
  "/knowledge": "Inteligencia documental",
  "/company": "Datos de empresa",
  "/plants": "Gestion de plantas",
  "/users": "Equipo y permisos",
  "/modules": "Modulos de trabajo",
  "/getting-started": "Primeros pasos",
  "/settings": "Seguridad y auditoria",
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const { company, isModuleEnabled, plants, plantsLoading, selectedPlantId, setSelectedPlantId } = useWorkspace();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const requiredModule = moduleForPath[pathname];
  const moduleBlocked = requiredModule && !isModuleEnabled(requiredModule);
  const accessBlocked = company && ["EXPIRED", "SUSPENDED"].includes(company.access_status) && !["/settings", "/getting-started"].includes(pathname);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  const sidebar = (
    <>
      <div className="flex h-18 items-center gap-3 border-b border-white/10 px-5 md:justify-center md:px-3 lg:justify-start lg:px-5">
        <div className="grid size-9 shrink-0 place-items-center rounded-md bg-[var(--brand)] text-[var(--brand-ink)]">
          <Gauge size={21} strokeWidth={2.4} />
        </div>
        <div className="min-w-0 md:hidden lg:block">
          <p className="text-base font-bold text-white">ForgeOps</p>
          <p className="text-[11px] font-semibold uppercase text-white/45">Industrial CMMS</p>
        </div>
        <button
          className="ml-auto text-white/60 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Cerrar menu"
        >
          <X size={20} />
        </button>
      </div>

      <nav className="sidebar-nav flex-1 overflow-y-auto px-3 py-4">
        <p className="nav-heading">Operacion</p>
        <div className="space-y-1">
          {primaryNavigation.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`nav-item ${active ? "nav-item-active" : ""}`}
                title={item.label}
              >
                <Icon size={19} />
                <span className="md:hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>

        <p className="nav-heading mt-5">Planificacion</p>
        <div className="space-y-1">
          {planningNavigation.filter((item) => isModuleEnabled(item.module)).map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`nav-item ${active ? "nav-item-active" : ""}`}
                title={item.label}
              >
                <Icon size={19} />
                <span className="md:hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>

        <p className="nav-heading mt-5">Inteligencia</p>
        <div className="space-y-1">
          {intelligenceNavigation.filter((item) => isModuleEnabled(item.module)).map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`nav-item ${active ? "nav-item-active" : ""}`}
                title={item.label}
              >
                <Icon size={19} />
                <span className="md:hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>

        <p className="nav-heading mt-5">Administracion</p>
        <div className="space-y-1">
          {administrationNavigation.filter((item) => !item.adminOnly || (user && ["SUPER_ADMIN", "ADMIN"].includes(user.role))).map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`nav-item ${active ? "nav-item-active" : ""}`}
                title={item.label}
              >
                <Icon size={19} />
                <span className="md:hidden lg:inline">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="grid grid-cols-3 gap-1 border-t border-white/10 p-3">
        <button onClick={() => setHelpOpen(true)} className="nav-item justify-center" title="Ayuda">
          <CircleHelp size={19} />
          <span className="hidden lg:inline">Ayuda</span>
        </button>
        <Link href="/settings" className={`nav-item justify-center ${pathname === "/settings" ? "nav-item-active" : ""}`} title="Seguridad">
          <ShieldCheck size={19} />
          <span className="hidden lg:inline">Seguridad</span>
        </Link>
        <button onClick={handleLogout} className="nav-item justify-center" title="Cerrar sesion">
          <LogOut size={19} />
          <span className="hidden lg:inline">Salir</span>
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-20 flex-col bg-[var(--sidebar)] md:flex lg:w-64">
        {sidebar}
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button className="absolute inset-0 bg-black/45" onClick={() => setMobileOpen(false)} aria-label="Cerrar menu" />
          <aside className="relative flex h-full w-72 flex-col bg-[var(--sidebar)]">{sidebar}</aside>
        </div>
      )}

      <div className="md:pl-20 lg:pl-64">
        <header className="sticky top-0 z-30 flex h-18 items-center border-b border-[var(--line)] bg-white/95 px-4 backdrop-blur md:px-6 lg:px-8">
          <button className="icon-button mobile-menu-button mr-3" onClick={() => setMobileOpen(true)} aria-label="Abrir menu">
            <Menu size={20} />
          </button>
          <div>
            <p className="text-[11px] font-bold uppercase text-[var(--muted)]">Centro de operaciones</p>
            <h1 className="text-[15px] font-bold text-[var(--ink)]">{pageNames[pathname] ?? "ForgeOps"}</h1>
          </div>
          <div className="ml-auto flex items-center gap-2 sm:gap-4">
            <label className="relative hidden sm:block">
              <span className="pointer-events-none absolute left-3 top-1/2 size-2 -translate-y-1/2 rounded-full bg-[var(--success)]" />
              <select
                aria-label="Planta activa"
                className="h-9 max-w-52 appearance-none rounded-md border border-[var(--line)] bg-white pl-7 pr-8 text-xs font-semibold text-[var(--ink-soft)]"
                value={selectedPlantId}
                onChange={(event) => setSelectedPlantId(event.target.value)}
                disabled={plantsLoading}
              >
                <option value="">Todas las plantas</option>
                {plants.map((plant) => (
                  <option key={plant.id} value={plant.id}>{plant.name}</option>
                ))}
              </select>
            </label>
            <button className="icon-button hidden sm:inline-grid" onClick={() => setHelpOpen(true)} aria-label="Abrir ayuda" title="Ayuda y tutorial">
              <CircleHelp size={18} />
            </button>
            <div className="h-8 w-px bg-[var(--line)]" />
            <Link href="/settings" className="flex items-center gap-2.5" title="Perfil y seguridad">
              <div className="grid size-9 place-items-center rounded-md bg-[var(--ink)] text-xs font-bold text-white">
                {initials(user?.full_name ?? "")}
              </div>
              <div className="hidden min-w-0 sm:block">
                <p className="max-w-40 truncate text-xs font-bold">{user?.full_name}</p>
                <p className="text-[10px] font-semibold text-[var(--muted)]">{user ? labelFor(user.role) : ""}</p>
              </div>
            </Link>
          </div>
        </header>
        {company && <TrialBanner company={company} />}
        <main className="p-4 md:p-6 lg:p-8">
          {accessBlocked && company ? (
            <AccessBlocked company={company} />
          ) : moduleBlocked ? (
            <ModuleUnavailable module={requiredModule} role={user?.role} />
          ) : children}
        </main>
      </div>
      <HelpDrawer open={helpOpen} onClose={() => setHelpOpen(false)} />
    </div>
  );
}
