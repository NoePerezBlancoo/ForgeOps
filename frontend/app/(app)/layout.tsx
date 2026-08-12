import { ProtectedShell } from "@/components/protected-shell";

export default function ApplicationLayout({ children }: { children: React.ReactNode }) {
  return <ProtectedShell>{children}</ProtectedShell>;
}

