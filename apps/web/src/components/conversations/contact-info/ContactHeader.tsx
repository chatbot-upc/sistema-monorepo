"use client";

import { Star, StarOff } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Pill } from "@/components/ui/Pill";
import { useToast } from "@/components/ui/ToastProvider";
import { toggleFavorite, type Conversation } from "@/lib/mock";
import { cn } from "@/lib/cn";

interface ContactHeaderProps {
  conversation: Conversation;
  favorite: boolean;
}

export function ContactHeader({ conversation, favorite }: ContactHeaderProps) {
  const { toast } = useToast();
  return (
    <div className="flex flex-col items-center text-center gap-2">
      <Avatar
        initials={conversation.initials}
        gradient={conversation.gradient}
        size="xl"
      />
      <div className="text-lg font-semibold tracking-[-0.3px] mt-1">
        {conversation.name}
      </div>
      <div className="font-mono text-xs text-muted">{conversation.phone}</div>
      <div className="flex items-center gap-2 mt-1">
        <Pill
          tone={
            conversation.status === "escalated"
              ? "escalated"
              : conversation.status === "active"
                ? "active"
                : "closed"
          }
        >
          {conversation.status === "escalated"
            ? "Escalada"
            : conversation.status === "active"
              ? "Activa"
              : "Cerrada"}
        </Pill>
        <button
          type="button"
          onClick={() => {
            toggleFavorite(conversation.id);
            toast.success(
              favorite ? "Removida de favoritos" : "Guardada en favoritos"
            );
          }}
          aria-label={favorite ? "Quitar de favoritos" : "Marcar como favorito"}
          className={cn(
            "w-7 h-7 rounded-full flex items-center justify-center transition-colors cursor-pointer",
            favorite
              ? "bg-amber-soft text-amber-fg"
              : "bg-surface-2 text-muted hover:text-fg-2"
          )}
        >
          {favorite ? (
            <Star size={14} strokeWidth={2} fill="currentColor" />
          ) : (
            <StarOff size={14} strokeWidth={2} />
          )}
        </button>
      </div>
    </div>
  );
}
