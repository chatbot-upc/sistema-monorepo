import Link from "next/link";
import { cn } from "@/lib/cn";
import type { ConvListFilter } from "./useConvListFilter";

interface FilterTabsProps {
  filter: ConvListFilter;
  counts: Record<ConvListFilter, number>;
  buildHref: (f: ConvListFilter) => string;
}

const TABS: { value: ConvListFilter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "escalated", label: "Escaladas" },
  { value: "active", label: "Activas" },
  { value: "closed", label: "Cerradas" },
];

export function FilterTabs({ filter, counts, buildHref }: FilterTabsProps) {
  return (
    <div className="flex gap-1.5 overflow-x-auto pb-0.5">
      {TABS.map((t) => (
        <Tab
          key={t.value}
          href={buildHref(t.value)}
          active={filter === t.value}
          label={t.label}
          count={counts[t.value]}
        />
      ))}
    </div>
  );
}

function Tab({
  href,
  active,
  label,
  count,
}: {
  href: string;
  active: boolean;
  label: string;
  count: number;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap flex items-center gap-1.5 cursor-pointer",
        active ? "bg-ink text-white" : "bg-surface-2 text-muted hover:text-fg-2"
      )}
    >
      {label}
      <span
        className={cn(
          "font-mono text-[10px] px-1.5 py-px rounded-full font-semibold",
          active ? "bg-white/20 text-white" : "bg-black/5 text-muted-2"
        )}
      >
        {count}
      </span>
    </Link>
  );
}
