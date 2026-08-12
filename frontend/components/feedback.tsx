import { AlertCircle, Inbox } from "lucide-react";

export function LoadingBlock() {
  return (
    <div className="grid min-h-64 place-items-center rounded-md border border-[var(--line)] bg-white">
      <div className="flex items-center gap-3 text-sm font-semibold text-[var(--muted)]">
        <span className="loader" /> Cargando informacion
      </div>
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="grid min-h-56 place-items-center px-6 text-center">
      <div>
        <Inbox className="mx-auto mb-3 text-[var(--muted)]" size={30} />
        <p className="text-sm font-bold text-[var(--ink)]">{title}</p>
        <p className="mt-1 text-sm text-[var(--muted)]">{detail}</p>
      </div>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-4 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800">
      <AlertCircle className="mt-0.5 shrink-0" size={17} /> {message}
    </div>
  );
}

