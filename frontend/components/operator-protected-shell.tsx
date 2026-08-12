"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { OperatorShell } from "@/components/operator-shell";
import { useOperatorAuth } from "@/components/operator-auth-provider";

export function OperatorProtectedShell({ children }: { children: React.ReactNode }) {
  const { operator, loading } = useOperatorAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !operator) router.replace("/control/login");
  }, [loading, operator, router]);

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-[var(--canvas)]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--muted)]">
          <span className="loader" /> Verificando acceso de operador
        </div>
      </div>
    );
  }
  if (!operator) return null;
  return <OperatorShell>{children}</OperatorShell>;
}
