import type { Metadata } from "next";

import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ForgeOps | Mantenimiento industrial",
    template: "%s | ForgeOps",
  },
  description: "Plataforma SaaS multiempresa para operaciones de mantenimiento industrial.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

