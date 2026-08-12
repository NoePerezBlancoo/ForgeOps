"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationBarProps {
  noun: string;
  page: number;
  pages: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function PaginationBar({ noun, page, pages, total, onPageChange }: PaginationBarProps) {
  return (
    <footer className="flex items-center justify-between gap-3 border-t border-[var(--line)] px-4 py-3">
      <p className="min-w-0 text-xs text-[var(--muted)]">
        {total} {noun} · pagina {page} de {pages}
      </p>
      <div className="flex shrink-0 gap-2">
        <button
          className="icon-button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Pagina anterior"
          title="Pagina anterior"
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="icon-button"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Pagina siguiente"
          title="Pagina siguiente"
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </footer>
  );
}
