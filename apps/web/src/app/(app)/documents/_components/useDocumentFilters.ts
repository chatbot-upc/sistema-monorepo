"use client";

import { useMemo, useState } from "react";
import type {
  DocumentRead,
  DocumentSourceType,
  DocumentStatus,
} from "@/lib/api/documents";

interface FiltersResult {
  search: string;
  setSearch: (v: string) => void;
  sourceFilter: DocumentSourceType[];
  setSourceFilter: (v: DocumentSourceType[]) => void;
  statusFilter: DocumentStatus[];
  setStatusFilter: (v: DocumentStatus[]) => void;
  filtered: DocumentRead[];
}

export function useDocumentFilters(items: DocumentRead[]): FiltersResult {
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<DocumentSourceType[]>([]);
  const [statusFilter, setStatusFilter] = useState<DocumentStatus[]>([]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((d) => {
      if (q && !d.title.toLowerCase().includes(q)) return false;
      if (sourceFilter.length > 0 && !sourceFilter.includes(d.source_type)) {
        return false;
      }
      if (statusFilter.length > 0 && !statusFilter.includes(d.status)) {
        return false;
      }
      return true;
    });
  }, [items, search, sourceFilter, statusFilter]);

  return {
    search,
    setSearch,
    sourceFilter,
    setSourceFilter,
    statusFilter,
    setStatusFilter,
    filtered,
  };
}
