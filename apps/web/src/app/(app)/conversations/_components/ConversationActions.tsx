"use client";

import { useState, useTransition } from "react";
import { Hand, HandMetal, Lock, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import {
  closeAction,
  releaseAction,
  reopenAction,
  takeoverAction,
} from "../_actions/conversations";
import type { ConversationStatus } from "@/lib/api/conversations";

interface Props {
  conversationId: number;
  status: ConversationStatus;
}

type ConfirmKey = "takeover" | "release" | "close" | "reopen" | null;

const COPY: Record<
  Exclude<ConfirmKey, null>,
  { title: string; description: string; confirmLabel: string }
> = {
  takeover: {
    title: "Tomar conversación",
    description:
      "El bot dejará de responder y tú podrás escribir directamente al estudiante por WhatsApp.",
    confirmLabel: "Tomar",
  },
  release: {
    title: "Liberar conversación",
    description: "El bot volverá a responder automáticamente al estudiante.",
    confirmLabel: "Liberar",
  },
  close: {
    title: "Cerrar conversación",
    description:
      "Quedará archivada. No se podrán enviar más mensajes hasta reabrirla.",
    confirmLabel: "Cerrar",
  },
  reopen: {
    title: "Reabrir conversación",
    description: "Volverá a estado Abierta y el bot podrá responder.",
    confirmLabel: "Reabrir",
  },
};

export function ConversationActions({ conversationId, status }: Props) {
  const [pending, startTransition] = useTransition();
  const [open, setOpen] = useState<ConfirmKey>(null);
  const { toast } = useToast();

  const run = (key: Exclude<ConfirmKey, null>) =>
    new Promise<void>((resolve, reject) => {
      startTransition(async () => {
        const action =
          key === "takeover"
            ? takeoverAction
            : key === "release"
              ? releaseAction
              : key === "close"
                ? closeAction
                : reopenAction;
        const result = await action(conversationId);
        if (result.ok) {
          toast.success("Acción aplicada");
          resolve();
        } else {
          toast.error("No se pudo aplicar", { description: result.error });
          reject(new Error(result.error));
        }
      });
    });

  return (
    <>
      <div className="flex items-center gap-2">
        {status === "abierta" && (
          <>
            <Button
              variant="secondary"
              size="sm"
              disabled={pending}
              onClick={() => setOpen("takeover")}
            >
              <Hand size={14} strokeWidth={2.5} />
              Tomar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={pending}
              onClick={() => setOpen("close")}
            >
              <Lock size={14} strokeWidth={2.5} />
              Cerrar
            </Button>
          </>
        )}
        {status === "takeover" && (
          <>
            <Button
              variant="secondary"
              size="sm"
              disabled={pending}
              onClick={() => setOpen("release")}
            >
              <HandMetal size={14} strokeWidth={2.5} />
              Liberar
            </Button>
            <Button
              variant="destructive"
              size="sm"
              disabled={pending}
              onClick={() => setOpen("close")}
            >
              <Lock size={14} strokeWidth={2.5} />
              Cerrar
            </Button>
          </>
        )}
        {status === "cerrada" && (
          <Button
            variant="secondary"
            size="sm"
            disabled={pending}
            onClick={() => setOpen("reopen")}
          >
            <RotateCcw size={14} strokeWidth={2.5} />
            Reabrir
          </Button>
        )}
      </div>

      {open && (
        <ConfirmDialog
          open
          onOpenChange={(v) => !v && setOpen(null)}
          title={COPY[open].title}
          description={COPY[open].description}
          confirmLabel={COPY[open].confirmLabel}
          variant={open === "close" ? "destructive" : "default"}
          onConfirm={() => run(open)}
        />
      )}
    </>
  );
}
