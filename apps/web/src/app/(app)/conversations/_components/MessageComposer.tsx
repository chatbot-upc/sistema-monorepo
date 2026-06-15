"use client";

import { useState, useTransition, type KeyboardEvent } from "react";
import { FileText, Paperclip, Reply, Send, X } from "lucide-react";
import { useToast } from "@/components/ui/ToastProvider";
import { sendMessageAction } from "../_actions/conversations";
import type {
  ConversationStatus,
  MessageRead,
  MessageRole,
} from "@/lib/api/conversations";

interface Props {
  conversationId: number;
  status: ConversationStatus;
  replyingTo: MessageRead | null;
  onCancelReply: () => void;
}

const MAX = 4096;

const ROLE_LABEL: Record<MessageRole, string> = {
  student: "Estudiante",
  bot: "Remi",
  admin: "Admin UPC",
};

export function MessageComposer({
  conversationId,
  status,
  replyingTo,
  onCancelReply,
}: Props) {
  const [body, setBody] = useState("");
  const [pending, startTransition] = useTransition();
  const { toast } = useToast();
  const disabled = status === "cerrada";

  const submit = () => {
    const text = body.trim();
    if (!text || pending || disabled) return;
    startTransition(async () => {
      const result = await sendMessageAction(
        conversationId,
        text,
        replyingTo?.id ?? null,
      );
      if (result.ok) {
        setBody("");
        onCancelReply();
        if (
          result.data.conversation_status === "takeover" &&
          status === "abierta"
        ) {
          toast.success("Mensaje enviado", {
            description: "La conversación pasó a Escalada (takeover).",
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
      <div className="border-t border-line px-6 py-4 text-[12px] text-muted-2 italic text-center">
        Esta conversación está cerrada. Reábrela para responder.
      </div>
    );
  }

  return (
    <div className="border-t border-line px-4 py-3">
      {replyingTo && (
        <div className="mb-2 flex items-start gap-2 rounded-xl border-l-2 border-primary bg-surface-2 px-3 py-2">
          <Reply size={14} strokeWidth={2.5} className="mt-0.5 shrink-0 text-primary" />
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-semibold text-primary">
              Respondiendo a {ROLE_LABEL[replyingTo.role]}
            </div>
            <div className="truncate text-[12px] text-muted">
              {replyingTo.content}
            </div>
          </div>
          <button
            type="button"
            onClick={onCancelReply}
            aria-label="Cancelar respuesta"
            className="shrink-0 rounded-full p-1 text-muted hover:bg-bg-2 hover:text-fg transition-colors"
          >
            <X size={14} strokeWidth={2.5} />
          </button>
        </div>
      )}
      <div className="flex items-end gap-2 rounded-2xl bg-surface-2 border border-line px-2 py-1.5 focus-within:border-primary transition-colors">
        <button
          type="button"
          onClick={() => toast.info("Adjuntar archivo — próximamente")}
          aria-label="Adjuntar archivo"
          className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center text-muted hover:text-primary hover:bg-bg-2 transition-colors"
        >
          <Paperclip size={17} strokeWidth={2} />
        </button>
        <button
          type="button"
          onClick={() => toast.info("Adjuntar documento — próximamente")}
          aria-label="Adjuntar documento"
          className="w-9 h-9 shrink-0 rounded-full flex items-center justify-center text-muted hover:text-primary hover:bg-bg-2 transition-colors"
        >
          <FileText size={17} strokeWidth={2} />
        </button>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Escribe una respuesta…"
          title="Cmd/Ctrl+Enter para enviar"
          maxLength={MAX}
          rows={1}
          disabled={pending}
          className="no-focus-outline flex-1 resize-none bg-transparent py-2 text-[13px] leading-relaxed placeholder:text-muted max-h-32 min-h-[20px]"
        />
        <button
          type="button"
          onClick={submit}
          disabled={pending || !body.trim()}
          className="shrink-0 inline-flex items-center gap-1.5 rounded-xl bg-primary text-white text-[13px] font-semibold px-4 py-2 hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {pending ? "Enviando…" : "Enviar"}
          <Send size={14} strokeWidth={2.5} />
        </button>
      </div>
    </div>
  );
}
