import { OperatorProtectedShell } from "@/components/operator-protected-shell";

export default function ControlPanelLayout({ children }: { children: React.ReactNode }) {
  return <OperatorProtectedShell>{children}</OperatorProtectedShell>;
}
