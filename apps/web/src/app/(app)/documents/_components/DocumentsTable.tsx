"use client";

import {
  FileText,
  MoreHorizontal,
  Eye,
  RefreshCw,
  Download,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { IconButton } from "@/components/ui/IconButton";
import { Dropdown } from "@/components/ui/Dropdown";
import { useToast } from "@/components/ui/ToastProvider";
import type { DocumentRead, DocumentStatus } from "@/lib/api/documents";

const STATUS_LABEL: Record<DocumentStatus, string> = {
  indexed: "Indexado",
  indexing: "Procesando",
  pending: "Pendiente",
  error: "Error",
};

const STATUS_TONE: Record<
  DocumentStatus,
  "active" | "pending" | "closed" | "escalated"
> = {
  indexed: "active",
  indexing: "pending",
  pending: "closed",
  error: "escalated",
};

interface DocumentsTableProps {
  rows: DocumentRead[];
  onDelete: (doc: DocumentRead) => void;
}

export function DocumentsTable({ rows, onDelete }: DocumentsTableProps) {
  return (
    <Card variant="flush">
      <div className="grid grid-cols-[1fr_110px_100px_140px_140px_60px] gap-4 px-6 py-4 bg-surface-2 font-mono text-[10px] uppercase tracking-[0.6px] text-muted font-semibold">
        <span>Nombre</span>
        <span>Fuente</span>
        <span>Chunks</span>
        <span>Estado</span>
        <span>Indexado</span>
        <span></span>
      </div>
      {rows.length === 0 && (
        <div className="px-6 py-16 text-center text-sm text-muted border-t border-line">
          Ningún documento coincide con los filtros.
        </div>
      )}
      {rows.map((d) => (
        <DocumentRow key={d.id} doc={d} onDelete={() => onDelete(d)} />
      ))}
    </Card>
  );
}

function formatIndexedAt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("es-PE", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: DocumentRead;
  onDelete: () => void;
}) {
  const { toast } = useToast();
  return (
    <div className="grid grid-cols-[1fr_110px_100px_140px_140px_60px] gap-4 px-6 py-4 items-center hover:bg-surface-2 transition-colors border-t border-line">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-blue-soft text-blue flex items-center justify-center shrink-0">
          <FileText size={16} strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold truncate">{doc.title}</div>
          {doc.status === "error" && doc.error_message ? (
            <div
              className="flex items-center gap-1 text-[11px] text-danger truncate"
              title={doc.error_message}
            >
              <AlertTriangle size={11} strokeWidth={2} />
              <span className="truncate">{doc.error_message}</span>
            </div>
          ) : (
            <div className="font-mono text-[10px] text-muted">
              v{doc.version} · sha256:{doc.sha256.slice(0, 7)}
            </div>
          )}
        </div>
      </div>
      <span className="font-mono text-xs font-semibold uppercase">
        {doc.source_type}
      </span>
      <span className="font-mono text-xs text-muted tabular">
        {doc.chunk_count}
      </span>
      <Pill tone={STATUS_TONE[doc.status]}>{STATUS_LABEL[doc.status]}</Pill>
      <span className="font-mono text-xs text-muted">
        {formatIndexedAt(doc.indexed_at)}
      </span>
      <Dropdown align="end">
        <Dropdown.Trigger>
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={`Acciones para ${doc.title}`}
          >
            <MoreHorizontal size={16} strokeWidth={2} />
          </IconButton>
        </Dropdown.Trigger>
        <Dropdown.Content>
          <Dropdown.Item
            icon={<Eye size={14} strokeWidth={2} />}
            onSelect={() =>
              toast.info(`Vista previa de ${doc.title}`, {
                description: "Próximamente: visor inline de documentos.",
              })
            }
          >
            Ver detalle
          </Dropdown.Item>
          <Dropdown.Item
            icon={<RefreshCw size={14} strokeWidth={2} />}
            disabled={doc.status === "indexing"}
            onSelect={() =>
              toast.info(`Reindexar ${doc.title}`, {
                description: "Disponible en HU14 (Sprint 4).",
              })
            }
          >
            Reindexar
          </Dropdown.Item>
          <Dropdown.Item
            icon={<Download size={14} strokeWidth={2} />}
            onSelect={() =>
              toast.info("Descarga simulada", {
                description: `${doc.title} estaría disponible en producción.`,
              })
            }
          >
            Descargar
          </Dropdown.Item>
          <Dropdown.Separator />
          <Dropdown.Item
            destructive
            icon={<Trash2 size={14} strokeWidth={2} />}
            onSelect={onDelete}
          >
            Eliminar
          </Dropdown.Item>
        </Dropdown.Content>
      </Dropdown>
    </div>
  );
}
