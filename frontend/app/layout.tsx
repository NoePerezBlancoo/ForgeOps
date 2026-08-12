import type { Metadata, Viewport } from "next";

import { AuthProvider } from "@/components/auth-provider";
import { PwaRuntime } from "@/components/pwa-runtime";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ForgeOps | Mantenimiento industrial",
    template: "%s | ForgeOps",
  },
  description: "Plataforma SaaS multiempresa para operaciones de mantenimiento industrial.",
  manifest: "/manifest.webmanifest",
  applicationName: "ForgeOps",
  icons: {
    icon: [
      { url: "/forgeops-icon.svg", type: "image/svg+xml" },
      { url: "/forgeops-icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    apple: "/forgeops-icon-192.png",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "ForgeOps",
  },
};

export const viewport: Viewport = {
  themeColor: "#142021",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>
          {children}
          <PwaRuntime />
        </AuthProvider>
      </body>
    </html>
  );
}
