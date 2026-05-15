"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Pagination } from "@/components/ui/Pagination";
import { useToast } from "@/components/ui/ToastProvider";
import type { DocumentRead, DocumentSummary } from "@/lib/api/documents";
import { deleteDocumentAction } from "../_actions/documents";
import { DocumentsStats } from "./DocumentsStats";
import { DocumentsToolbar } from "./DocumentsToolbar";
import { DocumentsTable } from "./DocumentsTable";
import { UploadDrawer } from "./UploadDrawer";
import { useDocumentFilters } from "./useDocumentFilters";

interface DocumentsViewProps {
  documents: DocumentRead[];
  currentPage: number;
  totalPages: number;
  total: number;
  summary: DocumentSummary;
}

export function DocumentsView({
  documents,
  currentPage,
  totalPages,
  total,
  summary,
}: DocumentsViewProps) {
  const { toast } = useToast();
  const filters = useDocumentFilters(documents);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<DocumentRead | null>(null);

  // Stats reflect the full catalog (from /documents/summary), not the page.
  const { indexed, indexing, total_chunks: totalChunks } = summary;

  return (
    <div className="flex flex-col gap-5">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
            Documentos
          </h1>
          <p className="text-sm text-muted mt-2">
            Fuentes que el chatbot consulta para responder con RAG
          </p>
        </div>
        <Button variant="dark" size="lg" onClick={() => setDrawerOpen(true)}>
          <Plus size={16} strokeWidth={2.5} />
          Subir documento
        </Button>
      </header>

      <DocumentsStats
        indexed={indexed}
        indexing={indexing}
        totalChunks={totalChunks}
      />

      <DocumentsToolbar
        search={filters.search}
        onSearch={filters.setSearch}
        sourceFilter={filters.sourceFilter}
        onSourceFilter={filters.setSourceFilter}
        statusFilter={filters.statusFilter}
        onStatusFilter={filters.setStatusFilter}
      />

      <DocumentsTable rows={filters.filtered} onDelete={setConfirmDelete} />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        total={total}
        itemLabelSingular="documento"
        itemLabelPlural="documentos"
      />

      <UploadDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />

      <ConfirmDialog
        open={!!confirmDelete}
        onOpenChange={(v) => !v && setConfirmDelete(null)}
        title={`¿Eliminar ${confirmDelete?.title ?? "este documento"}?`}
        description="El documento y sus fragmentos dejarán de aparecer en las respuestas RAG. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={async () => {
          if (!confirmDelete) return;
          const res = await deleteDocumentAction(confirmDelete.id);
          if (res.ok) {
            toast.success("Documento eliminado", {
              description: `${confirmDelete.title} y sus fragmentos fueron borrados.`,
            });
          } else {
            toast.error("No se pudo eliminar", { description: res.error });
          }
          setConfirmDelete(null);
        }}
      />
    </div>
  );
}
