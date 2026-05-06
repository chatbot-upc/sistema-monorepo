"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { Conversation, ConversationStatus } from "@/lib/mock";

export type ConvListFilter = "all" | "escalated" | "active" | "closed";

interface FilterResult {
  filter: ConvListFilter;
  search: string;
  setSearch: (v: string) => void;
  filtered: Conversation[];
  counts: Record<ConvListFilter, number>;
  buildHref: (f: ConvListFilter) => string;
}

export function useConvListFilter(
  items: Conversation[],
  activeId: string
): FilterResult {
  const searchParams = useSearchParams();
  const filter = (searchParams.get("filter") as ConvListFilter) ?? "all";
  const [search, setSearch] = useState("");

  const counts = useMemo(
    () => ({
      all: items.length,
      escalated: items.filter((c) => c.status === "escalated").length,
      active: items.filter((c) => c.status === "active").length,
      closed: items.filter((c) => c.status === "closed").length,
    }),
    [items]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((c) => {
      if (filter !== "all" && c.status !== (filter as ConversationStatus))
        return false;
      if (!q) return true;
      return (
        c.name.toLowerCase().includes(q) ||
        c.phone.toLowerCase().includes(q) ||
        c.studentId?.toLowerCase().includes(q)
      );
    });
  }, [items, search, filter]);

  const buildHref = (f: ConvListFilter) =>
    f === "all"
      ? `/conversations/${activeId}`
      : `/conversations/${activeId}?filter=${f}`;

  return { filter, search, setSearch, filtered, counts, buildHref };
}
