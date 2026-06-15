"use client";

import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Pagination } from "@/components/ui/Pagination";
import { useToast } from "@/components/ui/ToastProvider";
import { useConversationStream } from "@/lib/use-conversation-stream";
import type {
  DocumentRead,
  DocumentStatus,
  DocumentSummary,
  ProgramOption,
} from "@/lib/api/documents";
import { deleteDocumentAction } from "../_actions/documents";
import { requestWsTicket } from "../../conversations/_actions/ws-ticket";
import { DocumentsStats } from "./DocumentsStats";
import { DocumentsToolbar } from "./DocumentsToolbar";
import { DocumentsTable } from "./DocumentsTable";
import { UploadDrawer } from "./UploadDrawer";
import { useDocumentFilters } from "./useDocumentFilters";

type DocPatch = Partial<
  Pick<DocumentRead, "status" | "error_message" | "indexed_at" | "chunk_count">
>;

interface DocStatusEvent {
  document_id: number;
  status: DocumentStatus;
  indexed_at?: string;
  chunk_count?: number;
  error_message?: string;
}

interface DocumentsViewProps {
  documents: DocumentRead[];
  currentPage: number;
  totalPages: number;
  total: number;
  summary: DocumentSummary;
  programOptions: ProgramOption[];
}

export function DocumentsView({
  documents: initialDocuments,
  currentPage,
  totalPages,
  total,
  summary,
  programOptions,
}: DocumentsViewProps) {
  const { toast } = useToast();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<DocumentRead | null>(null);

  // Patches vivos provenientes del WebSocket; se aplican EN RENDER sobre los
  // datos del server. Sobreviven a router.refresh() hasta que el server-side
  // ya refleja el cambio. No usamos useEffect para sincronizar prop→state
  // (Vercel: rerender-derived-state-no-effect).
  const [patches, setPatches] = useState<Map<number, DocPatch>>(new Map());

  // Lista visible: patchea cada doc con su entry de WS (Map.get O(1)).
  const documents = useMemo(
    () =>
      initialDocuments.map((doc) => {
        const patch = patches.get(doc.id);
        return patch ? { ...doc, ...patch } : doc;
      }),
    [initialDocuments, patches],
  );

  // Stats delta: reduce funcional puro (sin mutación) sobre los patches.
  // Index Map para lookup O(1) de docs por id (Vercel: js-set-map-lookups).
  const statsAdjustment = useMemo(() => {
    const docsById = new Map(initialDocuments.map((d) => [d.id, d]));
    return Array.from(patches.entries()).reduce(
      (acc, [docId, patch]) => {
        const doc = docsById.get(docId);
        if (!doc) return acc;
        const newStatus = patch.status ?? doc.status;
        const indexedAdj =
          (newStatus === "indexed" ? 1 : 0) -
          (doc.status === "indexed" ? 1 : 0);
        const indexingAdj =
          (newStatus === "indexing" ? 1 : 0) -
          (doc.status === "indexing" ? 1 : 0);
        const chunkAdj =
          patch.chunk_count !== undefined &&
          patch.chunk_count !== doc.chunk_count
            ? patch.chunk_count - doc.chunk_count
            : 0;
        return {
          indexedDelta: acc.indexedDelta + indexedAdj,
          indexingDelta: acc.indexingDelta + indexingAdj,
          chunksDelta: acc.chunksDelta + chunkAdj,
        };
      },
      { indexedDelta: 0, indexingDelta: 0, chunksDelta: 0 },
    );
  }, [initialDocuments, patches]);

  const filters = useDocumentFilters(documents);

  useConversationStream(requestWsTicket, (event) => {
    if (event.type !== "document.status_changed") return;
    const data = event.data as DocStatusEvent;
    setPatches((prev) => {
      const next = new Map(prev);
      next.set(data.document_id, {
        status: data.status,
        error_message: data.error_message,
        indexed_at: data.indexed_at,
        chunk_count: data.chunk_count,
      });
      return next;
    });
  });

  // Stats vivas: catálogo completo del server + delta calculado en el useMemo
  // de arriba a partir de las transiciones observadas por WebSocket.
  const indexed = summary.indexed + statsAdjustment.indexedDelta;
  const indexing = summary.indexing + statsAdjustment.indexingDelta;
  const totalChunks = summary.total_chunks + statsAdjustment.chunksDelta;

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

      <UploadDrawer
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        programOptions={programOptions}
      />

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
