"use client";

import {
  Boxes,
  BrainCircuit,
  Building2,
  ChevronDown,
  ClipboardList,
  FileText,
  Gauge,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  Settings,
  ShieldAlert,
  Users,
  Wrench,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { initials, labelFor } from "@/lib/format";

const primaryNavigation = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/work-orders", label: "Ordenes de trabajo", icon: ClipboardList },
  { href: "/incidents", label: "Incidencias", icon: ShieldAlert },
  { href: "/assets", label: "Activos", icon: Boxes },
];

const planningNavigation = [
  { href: "/preventive-maintenance", label: "Preventivos", icon: Wrench },
  { href: "/inventory", label: "Inventario", icon: PackageSearch },
  { href: "/documents", label: "Documentos", icon: FileText },
];

const intelligenceNavigation = [
  { href: "/knowledge", label: "Asistente documental", icon: BrainCircuit },
];

const administrationNavigation = [
  { label: "Empresa", icon: Building2 },
  { label: "Usuarios", icon: Users },
  { label: "Configuracion", icon: Settings },
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
};

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

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
          {planningNavigation.map((item) => {
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
          {intelligenceNavigation.map((item) => {
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
          {administrationNavigation.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.label} className="nav-item cursor-not-allowed opacity-45" title={item.label}>
                <Icon size={19} />
                <span className="md:hidden lg:inline">{item.label}</span>
              </div>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-white/10 p-3">
        <button onClick={handleLogout} className="nav-item w-full" title="Cerrar sesion">
          <LogOut size={19} />
          <span className="md:hidden lg:inline">Cerrar sesion</span>
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
            <button className="hidden items-center gap-2 rounded-md border border-[var(--line)] bg-white px-3 py-2 text-xs font-semibold text-[var(--ink-soft)] sm:flex">
              <span className="size-2 rounded-full bg-[var(--success)]" /> Planta Ourense <ChevronDown size={14} />
            </button>
            <div className="h-8 w-px bg-[var(--line)]" />
            <div className="flex items-center gap-2.5">
              <div className="grid size-9 place-items-center rounded-md bg-[var(--ink)] text-xs font-bold text-white">
                {initials(user?.full_name ?? "")}
              </div>
              <div className="hidden min-w-0 sm:block">
                <p className="max-w-40 truncate text-xs font-bold">{user?.full_name}</p>
                <p className="text-[10px] font-semibold text-[var(--muted)]">{user ? labelFor(user.role) : ""}</p>
              </div>
            </div>
          </div>
        </header>
        <main className="p-4 md:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
