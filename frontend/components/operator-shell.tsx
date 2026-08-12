"use client";

import {
  Activity,
  Building2,
  Gauge,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  ShieldCheck,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useOperatorAuth } from "@/components/operator-auth-provider";
import { initials } from "@/lib/format";

const navigation = [
  { href: "/control", label: "Resumen", icon: LayoutDashboard },
  { href: "/control/companies", label: "Empresas", icon: Building2 },
  { href: "/control/audit", label: "Auditoria", icon: Activity },
  { href: "/control/security", label: "Seguridad", icon: LockKeyhole },
];

const pageNames: Record<string, string> = {
  "/control": "Resumen de plataforma",
  "/control/companies": "Empresas y suscripciones",
  "/control/audit": "Auditoria del operador",
  "/control/security": "Seguridad del operador",
};

export function OperatorShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { operator, logout } = useOperatorAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  async function handleLogout() {
    await logout();
    router.replace("/control/login");
  }

  const sidebar = (
    <>
      <div className="flex h-18 items-center gap-3 border-b border-white/10 px-5">
        <div className="grid size-9 shrink-0 place-items-center rounded-md bg-[var(--brand)] text-[var(--brand-ink)]">
          <Gauge size={21} strokeWidth={2.4} />
        </div>
        <div className="min-w-0">
          <p className="text-base font-bold text-white">ForgeOps</p>
          <p className="text-[10px] font-semibold uppercase text-white/45">Platform Control</p>
        </div>
        <button className="ml-auto text-white/60 md:hidden" onClick={() => setMobileOpen(false)} aria-label="Cerrar menu">
          <X size={20} />
        </button>
      </div>
      <div className="border-b border-white/10 px-5 py-4">
        <div className="flex items-center gap-2 text-[11px] font-bold text-white/70">
          <ShieldCheck size={15} className="text-[var(--brand)]" /> Entorno propietario
        </div>
        <p className="mt-1 text-[10px] leading-4 text-white/40">Separado de los espacios de clientes</p>
      </div>
      <nav className="sidebar-nav flex-1 px-3 py-4">
        <p className="nav-heading">Plataforma</p>
        <div className="space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)} className={`nav-item ${active ? "nav-item-active" : ""}`}>
                <Icon size={19} /> {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
      <div className="border-t border-white/10 p-3">
        <button onClick={handleLogout} className="nav-item w-full" title="Cerrar sesion">
          <LogOut size={19} /> Cerrar sesion
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col bg-[var(--sidebar)] md:flex">{sidebar}</aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button className="absolute inset-0 bg-black/45" onClick={() => setMobileOpen(false)} aria-label="Cerrar menu" />
          <aside className="relative flex h-full w-72 flex-col bg-[var(--sidebar)]">{sidebar}</aside>
        </div>
      )}
      <div className="md:pl-64">
        <header className="sticky top-0 z-30 flex h-18 items-center border-b border-[var(--line)] bg-white/95 px-4 backdrop-blur md:px-7">
          <button className="icon-button mobile-menu-button mr-3" onClick={() => setMobileOpen(true)} aria-label="Abrir menu"><Menu size={20} /></button>
          <div>
            <p className="text-[10px] font-bold uppercase text-[var(--accent)]">Control propietario</p>
            <h1 className="text-[15px] font-bold">{pageNames[pathname] ?? "ForgeOps Control"}</h1>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-xs font-bold">{operator?.full_name}</p>
              <p className="text-[10px] font-semibold text-[var(--muted)]">Operador con MFA</p>
            </div>
            <div className="grid size-9 place-items-center rounded-md bg-[var(--ink)] text-xs font-bold text-white">{initials(operator?.full_name ?? "")}</div>
          </div>
        </header>
        <main className="p-4 md:p-7 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
