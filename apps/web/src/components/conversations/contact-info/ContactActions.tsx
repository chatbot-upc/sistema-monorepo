"use client";

import { useState, type ReactNode } from "react";
import { Mail, Phone, AlertTriangle } from "lucide-react";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { blockConversation, type Conversation } from "@/lib/mock";
import { cn } from "@/lib/cn";

interface ContactActionsProps {
  conversation: Conversation;
  blocked: boolean;
}

export function ContactActions({ conversation, blocked }: ContactActionsProps) {
  const { toast } = useToast();
  const [callOpen, setCallOpen] = useState(false);
  const [blockOpen, setBlockOpen] = useState(false);

  return (
    <>
      <div className="grid grid-cols-3 gap-1.5">
        <ActionTile
          icon={<Mail size={16} strokeWidth={2} />}
          label="Email"
          onClick={() => {
            if (!conversation.email) {
              toast.error("Sin email registrado", {
                description: "Edita el contacto para agregar uno.",
              });
              return;
            }
            window.location.href = `mailto:${conversation.email}`;
          }}
        />
        <ActionTile
          icon={<Phone size={16} strokeWidth={2} />}
          label="Llamar"
          onClick={() => setCallOpen(true)}
        />
        <ActionTile
          icon={<AlertTriangle size={16} strokeWidth={2} />}
          label={blocked ? "Bloqueado" : "Bloquear"}
          warn
          disabled={blocked}
          onClick={() => setBlockOpen(true)}
        />
      </div>

      <ConfirmDialog
        open={callOpen}
        onOpenChange={setCallOpen}
        title={`Llamar a ${conversation.name}`}
        description={`Se iniciará una llamada al ${conversation.phone}.`}
        confirmLabel="Iniciar llamada"
        onConfirm={() => {
          toast.info("Llamada simulada", {
            description: `Marcando ${conversation.phone}...`,
          });
        }}
      />

      <ConfirmDialog
        open={blockOpen}
        onOpenChange={setBlockOpen}
        title={`¿Bloquear a ${conversation.name}?`}
        description="No volverá a recibir respuestas automáticas y la conversación quedará marcada como cerrada."
        confirmLabel="Bloquear"
        variant="destructive"
        onConfirm={() => {
          blockConversation(conversation.id);
          toast.success("Contacto bloqueado");
        }}
      />
    </>
  );
}

interface ActionTileProps {
  icon: ReactNode;
  label: string;
  warn?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

function ActionTile({ icon, label, warn, disabled, onClick }: ActionTileProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "bg-surface-2 rounded-xl p-3 px-2 flex flex-col items-center gap-2 cursor-pointer transition-colors",
        "hover:bg-line",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-surface-2"
      )}
    >
      <div
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          warn ? "bg-primary-soft text-primary" : "bg-surface text-fg-2"
        )}
      >
        {icon}
      </div>
      <span className="text-[11px] font-semibold text-fg-2">{label}</span>
    </button>
  );
}
