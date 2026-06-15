"use client";

import { useState } from "react";
import { Plus, CheckCircle2, Pencil, Trash2, Power } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { IconButton } from "@/components/ui/IconButton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { parseApiDate } from "@/lib/dates";
import type { PromptVersion } from "@/lib/api/prompts";
import { PromptEditorModal } from "./PromptEditorModal";
import {
  activatePromptVersionAction,
  deletePromptVersionAction,
} from "../_actions/prompts";

interface PromptsClientProps {
  versions: PromptVersion[];
}

function fmtDate(iso: string): string {
  return parseApiDate(iso).toLocaleString("es-PE", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function PromptsClient({ versions }: PromptsClientProps) {
  const { toast } = useToast();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<PromptVersion | null>(null);
  const [confirmActivate, setConfirmActivate] = useState<PromptVersion | null>(
    null,
  );
  const [confirmDelete, setConfirmDelete] = useState<PromptVersion | null>(null);

  const openCreate = () => {
    setEditing(null);
    setEditorOpen(true);
  };
  const openEdit = (v: PromptVersion) => {
    setEditing(v);
    setEditorOpen(true);
  };

  return (
    <div className="flex flex-col gap-5">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
            Prompt del chatbot
          </h1>
          <p className="text-sm text-muted mt-2">
            Versiona el system prompt del agente y activa el que quieras sin
            tocar código
          </p>
        </div>
        <Button variant="primary" size="lg" onClick={openCreate}>
          <Plus size={16} strokeWidth={2.5} />
          Nueva versión
        </Button>
      </header>

      <div className="flex flex-col gap-3">
        {versions.length === 0 ? (
          <div className="text-center text-muted text-sm py-16">
            Aún no hay versiones del prompt.
          </div>
        ) : (
          versions.map((v) => (
            <Card key={v.id} variant="flush" className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-[15px] font-semibold">
                      v{v.version}
                    </span>
                    {v.active ? (
                      <Pill tone="active">
                        <CheckCircle2 size={11} className="mr-1" />
                        Activa
                      </Pill>
                    ) : (
                      <Pill tone="closed">Inactiva</Pill>
                    )}
                    <span className="text-[11px] text-muted font-mono">
                      {fmtDate(v.created_at)}
                    </span>
                  </div>
                  <p className="text-[13px] text-muted mt-2 line-clamp-2 whitespace-pre-wrap">
                    {v.content.slice(0, 220)}
                    {v.content.length > 220 ? "…" : ""}
                  </p>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {!v.active && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setConfirmActivate(v)}
                    >
                      <Power size={14} strokeWidth={2.5} />
                      Activar
                    </Button>
                  )}
                  <IconButton
                    variant="ghost"
                    size="sm"
                    onClick={() => openEdit(v)}
                    aria-label={`Editar v${v.version}`}
                  >
                    <Pencil size={16} strokeWidth={2} />
                  </IconButton>
                  {!v.active && (
                    <IconButton
                      variant="ghost"
                      size="sm"
                      onClick={() => setConfirmDelete(v)}
                      aria-label={`Eliminar v${v.version}`}
                    >
                      <Trash2 size={16} strokeWidth={2} />
                    </IconButton>
                  )}
                </div>
              </div>
            </Card>
          ))
        )}
      </div>

      <PromptEditorModal
        open={editorOpen}
        onOpenChange={setEditorOpen}
        version={editing}
      />

      <ConfirmDialog
        open={confirmActivate !== null}
        onOpenChange={(o) => !o && setConfirmActivate(null)}
        title="Activar esta versión"
        description={
          confirmActivate
            ? `v${confirmActivate.version} pasará a ser el prompt activo del bot en vivo. La versión actual se desactiva.`
            : ""
        }
        confirmLabel="Activar"
        onConfirm={async () => {
          if (!confirmActivate) return;
          const v = confirmActivate.version;
          const result = await activatePromptVersionAction(confirmActivate.id);
          setConfirmActivate(null);
          if (result.ok) {
            toast.success(`v${v} activada`, {
              description: "El bot ya responde con este prompt.",
            });
          } else {
            toast.error("No se pudo activar", { description: result.error });
          }
        }}
      />

      <ConfirmDialog
        open={confirmDelete !== null}
        onOpenChange={(o) => !o && setConfirmDelete(null)}
        title="Eliminar versión"
        description={
          confirmDelete
            ? `Se eliminará v${confirmDelete.version} de forma permanente.`
            : ""
        }
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={async () => {
          if (!confirmDelete) return;
          const v = confirmDelete.version;
          const result = await deletePromptVersionAction(confirmDelete.id);
          setConfirmDelete(null);
          if (result.ok) {
            toast.success(`v${v} eliminada`);
          } else {
            toast.error("No se pudo eliminar", { description: result.error });
          }
        }}
      />
    </div>
  );
}
