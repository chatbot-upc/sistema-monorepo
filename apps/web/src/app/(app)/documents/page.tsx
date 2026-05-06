"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { useMockStore } from "@/lib/useMockStore";
import { deleteDocument, getDocuments, type Document } from "@/lib/mock";
import { DocumentsStats } from "./_components/DocumentsStats";
import { DocumentsToolbar } from "./_components/DocumentsToolbar";
import { DocumentsTable } from "./_components/DocumentsTable";
import { UploadDrawer } from "./_components/UploadDrawer";
import { useDocumentFilters } from "./_components/useDocumentFilters";

export default function DocumentsPage() {
  const documents = useMockStore(getDocuments);
  const { toast } = useToast();
  const filters = useDocumentFilters(documents);

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<Document | null>(null);

  const totalChunks = documents.reduce((acc, d) => acc + d.chunks, 0);
  const indexed = documents.filter((d) => d.status === "indexed").length;
  const indexing = documents.filter((d) => d.status === "indexing").length;

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
        typeFilter={filters.typeFilter}
        onTypeFilter={filters.setTypeFilter}
        statusFilter={filters.statusFilter}
        onStatusFilter={filters.setStatusFilter}
      />

      <DocumentsTable rows={filters.filtered} onDelete={setConfirmDelete} />

      <UploadDrawer open={drawerOpen} onOpenChange={setDrawerOpen} />

      <ConfirmDialog
        open={!!confirmDelete}
        onOpenChange={(v) => !v && setConfirmDelete(null)}
        title={`¿Eliminar ${confirmDelete?.name ?? "este documento"}?`}
        description="El documento dejará de aparecer en las respuestas RAG. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={async () => {
          if (!confirmDelete) return;
          deleteDocument(confirmDelete.id);
          toast.success("Documento eliminado", {
            description: `${confirmDelete.name} fue removido de la base de conocimiento.`,
          });
          setConfirmDelete(null);
        }}
      />
    </div>
  );
}
