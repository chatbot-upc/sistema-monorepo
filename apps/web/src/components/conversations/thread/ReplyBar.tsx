"use client";

import { useState, type KeyboardEvent } from "react";
import { Paperclip, FileText, Send } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";

interface ReplyBarProps {
  closed: boolean;
  onSend: (text: string) => void;
}

export function ReplyBar({ closed, onSend }: ReplyBarProps) {
  const [reply, setReply] = useState("");

  const submit = () => {
    const text = reply.trim();
    if (!text || closed) return;
    onSend(text);
    setReply("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <footer className="flex gap-2.5 items-end px-[18px] py-3.5 border-t border-line">
      <div className="flex gap-1.5 pb-1">
        <IconButton
          variant="ghost"
          size="sm"
          title="Adjuntar (próximamente)"
          aria-label="Adjuntar"
          disabled
        >
          <Paperclip size={16} strokeWidth={2} />
        </IconButton>
        <IconButton
          variant="ghost"
          size="sm"
          title="Plantillas (próximamente)"
          aria-label="Plantillas"
          disabled
        >
          <FileText size={16} strokeWidth={2} />
        </IconButton>
      </div>
      <textarea
        value={reply}
        onChange={(e) => setReply(e.target.value)}
        onKeyDown={onKey}
        disabled={closed}
        className="flex-1 bg-surface-2 border-none rounded-2xl px-4 py-3 resize-none text-sm min-h-11 max-h-30 leading-snug placeholder:text-muted-2 focus:outline-none focus:shadow-[0_0_0_2px_var(--color-primary)] disabled:opacity-50 disabled:cursor-not-allowed"
        placeholder={
          closed
            ? "Esta conversación está cerrada"
            : "Escribe tu respuesta... (⌘+Enter para enviar)"
        }
        rows={1}
      />
      <IconButton
        variant="primary"
        size="md"
        title="Enviar"
        aria-label="Enviar mensaje"
        onClick={submit}
        disabled={closed || reply.trim().length === 0}
      >
        <Send size={18} strokeWidth={2.5} />
      </IconButton>
    </footer>
  );
}
