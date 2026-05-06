"use client";

import { useMemo, useState } from "react";
import type { Document } from "@/lib/mock";

export type DocType = Document["type"];
export type DocStatus = Document["status"];

interface FiltersResult {
  search: string;
  setSearch: (v: string) => void;
  typeFilter: DocType[];
  setTypeFilter: (v: DocType[]) => void;
  statusFilter: DocStatus[];
  setStatusFilter: (v: DocStatus[]) => void;
  filtered: Document[];
}

export function useDocumentFilters(items: Document[]): FiltersResult {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<DocType[]>([]);
  const [statusFilter, setStatusFilter] = useState<DocStatus[]>([]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((d) => {
      if (q && !d.name.toLowerCase().includes(q)) return false;
      if (typeFilter.length > 0 && !typeFilter.includes(d.type)) return false;
      if (statusFilter.length > 0 && !statusFilter.includes(d.status))
        return false;
      return true;
    });
  }, [items, search, typeFilter, statusFilter]);

  return {
    search,
    setSearch,
    typeFilter,
    setTypeFilter,
    statusFilter,
    setStatusFilter,
    filtered,
  };
}
