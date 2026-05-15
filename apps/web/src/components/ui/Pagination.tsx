"use client";

import { useTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  total: number;
  itemLabelSingular?: string;
  itemLabelPlural?: string;
  /** Param key used in the URL. Default "page". */
  paramKey?: string;
}

export function Pagination({
  currentPage,
  totalPages,
  total,
  itemLabelSingular = "elemento",
  itemLabelPlural = "elementos",
  paramKey = "page",
}: PaginationProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  if (totalPages <= 1) {
    return (
      <div className="flex items-center justify-between px-2 text-[12px] text-muted font-mono">
        <span>
          {total} {total === 1 ? itemLabelSingular : itemLabelPlural}
        </span>
      </div>
    );
  }

  const goTo = (page: number) => {
    if (page < 1 || page > totalPages || page === currentPage) return;
    const next = new URLSearchParams(searchParams.toString());
    if (page === 1) {
      next.delete(paramKey);
    } else {
      next.set(paramKey, String(page));
    }
    const qs = next.toString();
    startTransition(() => {
      router.push(qs ? `?${qs}` : "?");
    });
  };

  const prevDisabled = currentPage <= 1 || isPending;
  const nextDisabled = currentPage >= totalPages || isPending;

  return (
    <div className="flex items-center justify-between px-2 text-[12px] text-muted font-mono">
      <span>
        Página{" "}
        <span className="text-fg font-semibold tabular">{currentPage}</span> de{" "}
        <span className="tabular">{totalPages}</span>
        {" · "}
        {total} {total === 1 ? itemLabelSingular : itemLabelPlural}
      </span>
      <div className="flex items-center gap-2">
        {isPending && (
          <Loader2
            size={14}
            className="animate-spin text-muted-2"
            aria-hidden
          />
        )}
        <PaginatorButton
          onClick={() => goTo(currentPage - 1)}
          disabled={prevDisabled}
          aria-label="Página anterior"
        >
          <ChevronLeft size={14} strokeWidth={2.5} />
          Anterior
        </PaginatorButton>
        <PaginatorButton
          onClick={() => goTo(currentPage + 1)}
          disabled={nextDisabled}
          aria-label="Página siguiente"
        >
          Siguiente
          <ChevronRight size={14} strokeWidth={2.5} />
        </PaginatorButton>
      </div>
    </div>
  );
}

function PaginatorButton({
  children,
  className,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...rest}
      className={cn(
        "inline-flex items-center gap-1 h-8 px-3 rounded-full border border-line bg-surface",
        "text-[12px] text-fg font-semibold cursor-pointer",
        "hover:bg-bg-2 transition-colors",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-surface",
        className,
      )}
    >
      {children}
    </button>
  );
}
