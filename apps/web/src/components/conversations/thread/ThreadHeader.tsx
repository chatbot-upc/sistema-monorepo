"use client";

import { Phone, Info, X } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { IconButton } from "@/components/ui/IconButton";
import type { Conversation } from "@/lib/mock";
import { StatusLabel } from "./MessageBubble";

interface ThreadHeaderProps {
  conversation: Conversation;
  messageCount: number;
  firstMessageTime?: string;
  closed: boolean;
  onCall: () => void;
  onToggleContact?: () => void;
  onClose: () => void;
}

export function ThreadHeader({
  conversation,
  messageCount,
  firstMessageTime,
  closed,
  onCall,
  onToggleContact,
  onClose,
}: ThreadHeaderProps) {
  return (
    <header className="flex items-center gap-3.5 px-6 py-[18px] border-b border-line">
      <Avatar
        initials={conversation.initials}
        gradient={conversation.gradient}
        size="md"
      />
      <div className="flex-1 min-w-0">
        <div className="text-base font-semibold tracking-[-0.2px]">
          {conversation.name}
        </div>
        <div className="font-mono text-[11px] text-muted mt-0.5">
          {conversation.phone} · <StatusLabel status={conversation.status} />{" "}
          {firstMessageTime && `desde ${firstMessageTime}`} · {messageCount}{" "}
          mensajes
        </div>
      </div>
      <div className="flex gap-1.5">
        <IconButton
          variant="ghost"
          size="sm"
          title="Llamar"
          aria-label="Llamar"
          onClick={onCall}
        >
          <Phone size={16} strokeWidth={2} />
        </IconButton>
        <IconButton
          variant="ghost"
          size="sm"
          title="Información"
          aria-label="Información del contacto"
          onClick={onToggleContact}
        >
          <Info size={16} strokeWidth={2} />
        </IconButton>
        <IconButton
          variant="primary-soft"
          size="sm"
          title={closed ? "Conversación cerrada" : "Cerrar"}
          aria-label="Cerrar conversación"
          onClick={onClose}
          disabled={closed}
        >
          <X size={16} strokeWidth={2} />
        </IconButton>
      </div>
    </header>
  );
}
