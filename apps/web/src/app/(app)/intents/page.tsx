"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { useMockStore } from "@/lib/useMockStore";
import { deleteIntent, getIntents, type Intent } from "@/lib/mock";
import { IntentsStats } from "./_components/IntentsStats";
import { IntentRow } from "./_components/IntentRow";
import { IntentEditorModal } from "./_components/IntentEditorModal";

export default function IntentsPage() {
  const intents = useMockStore(getIntents);
  const { toast } = useToast();
  // Lazy init para evitar evaluar el initializer en cada render
  // (Vercel rule: rerender-lazy-state-init).
  const [expanded, setExpanded] = useState<string | null>(
    () => intents[0]?.id ?? null
  );
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Intent | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Intent | null>(null);

  // Reconciliación derivada en render: si la intent expandida fue eliminada,
  // tratamos expanded como null para que ningún row aparezca abierto vacío.
  // (Vercel rule: rerender-derived-state-no-effect).
  const expandedSafe =
    expanded !== null && intents.some((i) => i.id === expanded)
      ? expanded
      : null;

  const openCreate = () => {
    setEditing(null);
    setEditorOpen(true);
  };

  const openEdit = (intent: Intent) => {
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
        {intents.map((intent) => (
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
        ))}
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
        onConfirm={() => {
          if (!confirmDelete) return;
          const name = confirmDelete.name;
          deleteIntent(confirmDelete.id);
          setConfirmDelete(null);
          toast.success("Intención eliminada", {
            description: `${name} ya no se considera al clasificar.`,
          });
        }}
      />
    </div>
  );
}
