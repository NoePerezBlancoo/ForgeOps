import type { CompanyModule } from "@/lib/types";

export const moduleCatalog: Record<CompanyModule, {
  title: string;
  shortDescription: string;
  description: string;
  href: string;
}> = {
  PREVENTIVE: {
    title: "Mantenimiento preventivo",
    shortDescription: "Planes recurrentes y generacion de ordenes.",
    description: "Programa intervenciones recurrentes y convierte cada vencimiento en trabajo trazable.",
    href: "/preventive-maintenance",
  },
  INVENTORY: {
    title: "Inventario de repuestos",
    shortDescription: "Stock, minimos y movimientos.",
    description: "Controla existencias, consumos y alertas de material critico para mantenimiento.",
    href: "/inventory",
  },
  DOCUMENTS: {
    title: "Documentacion tecnica",
    shortDescription: "Manuales y procedimientos por activo.",
    description: "Centraliza documentos tecnicos y conserva su relacion con cada equipo industrial.",
    href: "/documents",
  },
  KNOWLEDGE: {
    title: "Asistente documental",
    shortDescription: "Consulta tecnica con fuentes verificables.",
    description: "Pregunta sobre la documentacion indexada y recibe respuestas trazadas a sus fuentes.",
    href: "/knowledge",
  },
};

export const moduleForPath: Record<string, CompanyModule> = {
  "/preventive-maintenance": "PREVENTIVE",
  "/inventory": "INVENTORY",
  "/documents": "DOCUMENTS",
  "/knowledge": "KNOWLEDGE",
};
