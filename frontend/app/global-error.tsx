"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="es">
      <body style={{ margin: 0, background: "#eef1ef", color: "#142021", fontFamily: "Arial, sans-serif" }}>
        <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
          <section style={{ maxWidth: 460, textAlign: "center" }}>
            <h1 style={{ fontSize: 26 }}>ForgeOps no pudo iniciar</h1>
            <p style={{ color: "#60706f", lineHeight: 1.6 }}>
              Se ha producido un error inesperado. La operacion puede reintentarse de forma segura.
            </p>
            <button
              onClick={reset}
              style={{ marginTop: 16, border: 0, borderRadius: 6, background: "#16756f", color: "white", padding: "11px 18px", fontWeight: 700 }}
            >
              Reintentar
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
