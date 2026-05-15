"use client";

import { Search } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Select, type SelectOption } from "@/components/ui/Select";
import type { DocumentSourceType, DocumentStatus } from "@/lib/api/documents";

const SOURCE_OPTIONS: SelectOption<DocumentSourceType>[] = [
  { value: "upload", label: "Subido" },
  { value: "scraped", label: "Scrapeado" },
  { value: "link", label: "Enlace" },
];

const STATUS_OPTIONS: SelectOption<DocumentStatus>[] = [
  { value: "indexed", label: "Indexado" },
  { value: "indexing", label: "Procesando" },
  { value: "pending", label: "Pendiente" },
  { value: "error", label: "Error" },
];

interface DocumentsToolbarProps {
  search: string;
  onSearch: (v: string) => void;
  sourceFilter: DocumentSourceType[];
  onSourceFilter: (v: DocumentSourceType[]) => void;
  statusFilter: DocumentStatus[];
  onStatusFilter: (v: DocumentStatus[]) => void;
}

export function DocumentsToolbar({
  search,
  onSearch,
  sourceFilter,
  onSourceFilter,
  statusFilter,
  onStatusFilter,
}: DocumentsToolbarProps) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="flex-1 bg-surface-2 rounded-full px-4 py-2.5 pl-11 relative">
        <Search
          size={16}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-muted"
          strokeWidth={2}
        />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          className="bg-transparent border-none w-full text-[13px] focus:outline-none placeholder:text-muted-2"
          placeholder="Buscar documento..."
        />
      </div>
      <Select
        multi
        options={SOURCE_OPTIONS}
        value={sourceFilter}
        onChange={onSourceFilter}
        label="Fuente"
      />
      <Select
        multi
        options={STATUS_OPTIONS}
        value={statusFilter}
        onChange={onStatusFilter}
        label="Estado"
        align="end"
      />
    </Card>
  );
}
