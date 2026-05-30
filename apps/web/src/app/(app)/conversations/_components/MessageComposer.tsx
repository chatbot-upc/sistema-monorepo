"use client";

import { useState, useTransition, type KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/ToastProvider";
import { sendMessageAction } from "../_actions/conversations";
import type { ConversationStatus } from "@/lib/api/conversations";

interface Props {
  conversationId: number;
  status: ConversationStatus;
}

const MAX = 4096;

export function MessageComposer({ conversationId, status }: Props) {
  const [body, setBody] = useState("");
  const [pending, startTransition] = useTransition();
  const { toast } = useToast();
  const disabled = status === "cerrada";

  const submit = () => {
    const text = body.trim();
    if (!text || pending || disabled) return;
    startTransition(async () => {
      const result = await sendMessageAction(conversationId, text);
      if (result.ok) {
        setBody("");
        if (result.data.conversation_status === "takeover" && status === "abierta") {
          toast.success("Mensaje enviado", {
            description: "La conversación pasó a Derivada (takeover).",
          });
        }
      } else {
        toast.error("No se pudo enviar", { description: result.error });
      }
    });
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  };

  if (disabled) {
    return (
      <div className="border-t border-line px-6 py-3 text-[12px] text-muted-2 italic">
        Esta conversación está cerrada. Reábrela para responder.
      </div>
    );
  }

  return (
    <div className="border-t border-line px-4 py-3 flex flex-col gap-2">
      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Escribe una respuesta… (Cmd/Ctrl+Enter para enviar)"
        maxLength={MAX}
        showCounter
        rows={3}
        disabled={pending}
      />
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-2">
          {status === "abierta"
            ? "Se enviará por WhatsApp y la conversación pasará a Derivada."
            : "Se enviará por WhatsApp."}
        </span>
        <Button
          variant="primary"
          size="sm"
          onClick={submit}
          disabled={pending || !body.trim()}
        >
          <Send size={14} strokeWidth={2.5} />
          {pending ? "Enviando…" : "Enviar"}
        </Button>
      </div>
    </div>
  );
}
