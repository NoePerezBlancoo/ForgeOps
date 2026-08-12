"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { WorkspaceProvider } from "@/components/workspace-provider";

export function ProtectedShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-[var(--canvas)]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--muted)]">
          <span className="loader" /> Preparando centro de operaciones
        </div>
      </div>
    );
  }

  if (!user) return null;
  return (
    <WorkspaceProvider>
      <AppShell>{children}</AppShell>
    </WorkspaceProvider>
  );
}
