"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import type { IntentRead } from "@/lib/api/intents";
import { deleteIntentAction } from "../_actions/intents";
import { IntentsStats } from "./IntentsStats";
import { IntentRow } from "./IntentRow";
import { IntentEditorModal } from "./IntentEditorModal";

interface IntentsClientProps {
  intents: IntentRead[];
}

export function IntentsClient({ intents }: IntentsClientProps) {
  const { toast } = useToast();
  const [expanded, setExpanded] = useState<number | null>(
    () => intents[0]?.id ?? null,
  );
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<IntentRead | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<IntentRead | null>(null);

  // Reconciliación derivada en render: si la intent expandida ya no existe
  // (tras un revalidate), tratamos expanded como null.
  const expandedSafe =
    expanded !== null && intents.some((i) => i.id === expanded)
      ? expanded
      : null;

  const openCreate = () => {
    setEditing(null);
    setEditorOpen(true);
  };

  const openEdit = (intent: IntentRead) => {
    setEditing(intent);
    setEditorOpen(true);
  };

  return (
    <div className="flex flex-col gap-5">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
            Intenciones
          </h1>
          <p className="text-sm text-muted mt-2">
            Categorías que el modelo SBERT clasifica para responder con
            plantillas o RAG
          </p>
        </div>
        <Button variant="primary" size="lg" onClick={openCreate}>
          <Plus size={16} strokeWidth={2.5} />
          Nueva intención
        </Button>
      </header>

      <IntentsStats intents={intents} />

      <div className="flex flex-col gap-3">
        {intents.length === 0 ? (
          <div className="text-center text-muted text-sm py-16">
            Aún no hay intenciones. Crea la primera con &ldquo;Nueva
            intención&rdquo;.
          </div>
        ) : (
          intents.map((intent) => (
            <IntentRow
              key={intent.id}
              intent={intent}
              open={expandedSafe === intent.id}
              onToggle={() =>
                setExpanded(expandedSafe === intent.id ? null : intent.id)
              }
              onEdit={() => openEdit(intent)}
              onDelete={() => setConfirmDelete(intent)}
            />
          ))
        )}
      </div>

      <IntentEditorModal
        open={editorOpen}
        onOpenChange={setEditorOpen}
        intent={editing}
      />

      <ConfirmDialog
        open={confirmDelete !== null}
        onOpenChange={(v) => !v && setConfirmDelete(null)}
        title="Eliminar intención"
        description={
          confirmDelete
            ? `Se quitará "${confirmDelete.name}" del clasificador. Esta acción no se puede deshacer.`
            : ""
        }
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={async () => {
          if (!confirmDelete) return;
          const name = confirmDelete.name;
          const result = await deleteIntentAction(confirmDelete.id);
          setConfirmDelete(null);
          if (result.ok) {
            toast.success("Intención eliminada", {
              description: `${name} ya no se considera al clasificar.`,
            });
          } else {
            toast.error("No se pudo eliminar", { description: result.error });
          }
        }}
      />
    </div>
  );
}
