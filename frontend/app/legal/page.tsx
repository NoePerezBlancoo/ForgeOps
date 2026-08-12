import { ArrowLeft, Gauge, ShieldCheck } from "lucide-react";
import Link from "next/link";

export default function LegalPage() {
  return (
    <main className="min-h-screen bg-[var(--canvas)] px-5 py-10 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <header className="flex items-center justify-between border-b border-[var(--line)] pb-6">
          <div className="flex items-center gap-3"><div className="grid size-9 place-items-center rounded-md bg-[var(--ink)] text-[var(--brand)]"><Gauge size={20} /></div><div><p className="font-bold">ForgeOps</p><p className="text-[10px] font-semibold uppercase text-[var(--muted)]">Evaluacion profesional</p></div></div>
          <Link className="button-secondary" href="/login"><ArrowLeft size={15} /> Volver</Link>
        </header>

        <article className="py-8">
          <p className="text-xs font-bold uppercase text-[var(--accent)]">Condiciones de evaluacion</p>
          <h1 className="mt-3 text-3xl font-bold">Prueba de ForgeOps durante 30 dias</h1>
          <p className="mt-4 text-sm leading-7 text-[var(--muted)]">Estas condiciones describen el entorno demostrativo incluido en este proyecto. Antes de una explotacion comercial publica deben adaptarse con los datos legales, politica de privacidad y contratos del titular del servicio.</p>

          <div className="mt-8 space-y-7 text-sm leading-7 text-[var(--ink-soft)]">
            <Section title="Finalidad">La cuenta se facilita para evaluar las funciones de mantenimiento industrial. No debe utilizarse como unico sistema para decisiones que afecten a seguridad de personas o instalaciones.</Section>
            <Section title="Duracion y acceso">La prueba dura 30 dias desde el registro. Al vencer, el acceso operativo queda bloqueado y los datos se conservan temporalmente para facilitar una posible continuidad o exportacion acordada.</Section>
            <Section title="Datos">Cada empresa dispone de un espacio logico aislado. No deben cargarse secretos industriales, datos especialmente protegidos ni documentacion cuya cesion no este autorizada.</Section>
            <Section title="Seguridad">Las contrasenas se almacenan mediante hash y las sesiones son revocables. El usuario es responsable de custodiar sus credenciales y de asignar permisos adecuados a su equipo.</Section>
            <Section title="Inteligencia documental">El modo local no envia documentos a proveedores externos. Si el operador habilita un proveedor de IA, debe informar y obtener las autorizaciones aplicables antes de procesar documentacion empresarial.</Section>
          </div>

          <div className="mt-9 flex items-start gap-3 border-l-4 border-l-[var(--accent)] bg-white p-5"><ShieldCheck className="mt-0.5 shrink-0 text-[var(--accent)]" size={20} /><p className="text-xs leading-6 text-[var(--muted)]">Documento funcional para demostracion del producto. Requiere revision juridica y datos del responsable antes de ofrecer ForgeOps como servicio comercial.</p></div>
        </article>
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return <section><h2 className="font-bold text-[var(--ink)]">{title}</h2><p className="mt-1">{children}</p></section>;
}
