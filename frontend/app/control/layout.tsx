import type { Metadata } from "next";

import { OperatorAuthProvider } from "@/components/operator-auth-provider";

export const metadata: Metadata = {
  title: "Control de plataforma",
  robots: { index: false, follow: false },
};

export default function ControlLayout({ children }: { children: React.ReactNode }) {
  return <OperatorAuthProvider>{children}</OperatorAuthProvider>;
}
