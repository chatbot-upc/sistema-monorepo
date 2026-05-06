"use client";

import {
  FileText,
  MoreHorizontal,
  Eye,
  RefreshCw,
  Download,
  Trash2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { IconButton } from "@/components/ui/IconButton";
import { Dropdown } from "@/components/ui/Dropdown";
import { useToast } from "@/components/ui/ToastProvider";
import { reindexDocument, type Document } from "@/lib/mock";
import type { DocStatus } from "./useDocumentFilters";

const STATUS_LABEL: Record<DocStatus, string> = {
  indexed: "Indexado",
  indexing: "Procesando",
  draft: "Borrador",
  error: "Error",
};

const STATUS_TONE: Record<
  DocStatus,
  "active" | "pending" | "closed" | "escalated"
> = {
  indexed: "active",
  indexing: "pending",
  draft: "closed",
  error: "escalated",
};

interface DocumentsTableProps {
  rows: Document[];
  onDelete: (doc: Document) => void;
}

export function DocumentsTable({ rows, onDelete }: DocumentsTableProps) {
  return (
    <Card variant="flush">
      <div className="grid grid-cols-[1fr_100px_120px_140px_140px_60px] gap-4 px-6 py-4 bg-surface-2 font-mono text-[10px] uppercase tracking-[0.6px] text-muted font-semibold">
        <span>Nombre</span>
        <span>Tipo</span>
        <span>Tamaño</span>
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

function DocumentRow({
  doc,
  onDelete,
}: {
  doc: Document;
  onDelete: () => void;
}) {
  const { toast } = useToast();
  return (
    <div className="grid grid-cols-[1fr_100px_120px_140px_140px_60px] gap-4 px-6 py-4 items-center hover:bg-surface-2 transition-colors border-t border-line">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-9 h-9 rounded-xl bg-blue-soft text-blue flex items-center justify-center shrink-0">
          <FileText size={16} strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold truncate">{doc.name}</div>
          <div className="font-mono text-[10px] text-muted">
            {doc.chunks > 0 ? `${doc.chunks} chunks` : "—"}
          </div>
        </div>
      </div>
      <span className="font-mono text-xs font-semibold uppercase">
        {doc.type}
      </span>
      <span className="font-mono text-xs text-muted">{doc.size}</span>
      <Pill tone={STATUS_TONE[doc.status]}>{STATUS_LABEL[doc.status]}</Pill>
      <span className="font-mono text-xs text-muted">
        {doc.indexedAt ?? "—"}
      </span>
      <Dropdown align="end">
        <Dropdown.Trigger>
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={`Acciones para ${doc.name}`}
          >
            <MoreHorizontal size={16} strokeWidth={2} />
          </IconButton>
        </Dropdown.Trigger>
        <Dropdown.Content>
          <Dropdown.Item
            icon={<Eye size={14} strokeWidth={2} />}
            onSelect={() =>
              toast.info(`Vista previa de ${doc.name}`, {
                description: "Próximamente: visor inline de documentos.",
              })
            }
          >
            Ver detalle
          </Dropdown.Item>
          <Dropdown.Item
            icon={<RefreshCw size={14} strokeWidth={2} />}
            disabled={doc.status === "indexing"}
            onSelect={() => {
              reindexDocument(doc.id);
              toast.info(`Reindexando ${doc.name}`, {
                description: "Esto puede tardar unos segundos.",
              });
            }}
          >
            Reindexar
          </Dropdown.Item>
          <Dropdown.Item
            icon={<Download size={14} strokeWidth={2} />}
            onSelect={() =>
              toast.info("Descarga simulada", {
                description: `${doc.name} estaría disponible en producción.`,
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
