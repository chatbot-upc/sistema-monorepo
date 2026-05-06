"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { useMockStore } from "@/lib/useMockStore";
import {
  appendMessage,
  closeConversation,
  getConversations,
  getThread,
} from "@/lib/mock";
import { ThreadHeader } from "./thread/ThreadHeader";
import { MessageBubble } from "./thread/MessageBubble";
import { ReplyBar } from "./thread/ReplyBar";
import { useThreadScroll } from "./thread/useThreadScroll";

interface ThreadProps {
  conversationId: string;
  onToggleContact?: () => void;
}

export function Thread({ conversationId, onToggleContact }: ThreadProps) {
  const conversations = useMockStore(getConversations);
  const messages = useMockStore(() => getThread(conversationId));
  const conversation = conversations.find((c) => c.id === conversationId);

  const router = useRouter();
  const { toast } = useToast();
  const [callOpen, setCallOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useThreadScroll(scrollRef, `${conversationId}-${messages.length}`);

  if (!conversation) {
    return (
      <section className="bg-surface rounded-3xl flex flex-col flex-1 min-w-0 items-center justify-center text-sm text-muted">
        Conversación no encontrada.
      </section>
    );
  }

  const closed = conversation.status === "closed";

  const sendReply = (text: string) => {
    appendMessage(conversationId, {
      id: `m-${Date.now().toString(36)}`,
      author: "admin",
      text,
      time: new Date().toLocaleTimeString("es-PE", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
      adminName: "Renzo",
    });
  };

  return (
    <section className="bg-surface rounded-3xl flex flex-col flex-1 min-w-0 overflow-hidden">
      <ThreadHeader
        conversation={conversation}
        messageCount={messages.length}
        firstMessageTime={messages[0]?.time}
        closed={closed}
        onCall={() => setCallOpen(true)}
        onToggleContact={onToggleContact}
        onClose={() => setCloseOpen(true)}
      />

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 flex flex-col gap-2.5">
        {messages.length === 0 && (
          <div className="self-center text-sm text-muted py-8">
            No hay mensajes todavía. Envía el primero abajo.
          </div>
        )}
        {messages.map((m, idx) => {
          const showNotice =
            idx > 0 &&
            messages[idx - 1].author === "student" &&
            m.author === "admin";
          return (
            <div key={m.id} className="flex flex-col gap-2.5">
              {showNotice && (
                <div className="self-center font-mono text-[10px] text-muted bg-surface-2 px-3.5 py-1.5 rounded-full uppercase tracking-[0.4px] font-semibold my-1.5">
                  Conversación escalada · {m.time}
                </div>
              )}
              <MessageBubble msg={m} />
            </div>
          );
        })}
      </div>

      <ReplyBar closed={closed} onSend={sendReply} />

      <ConfirmDialog
        open={callOpen}
        onOpenChange={setCallOpen}
        title={`Llamar a ${conversation.name}`}
        description={`Se iniciará una llamada al ${conversation.phone}. Esta función está simulada en este demo.`}
        confirmLabel="Iniciar llamada"
        onConfirm={() => {
          toast.info("Llamada simulada", {
            description: `Marcando ${conversation.phone}...`,
          });
        }}
      />

      <ConfirmDialog
        open={closeOpen}
        onOpenChange={setCloseOpen}
        title="¿Cerrar esta conversación?"
        description="El estudiante recibirá un mensaje de despedida automático y la conversación pasará al estado cerrada."
        confirmLabel="Cerrar conversación"
        variant="destructive"
        onConfirm={() => {
          closeConversation(conversationId);
          toast.success("Conversación cerrada", {
            description: "El chat ahora aparece en el filtro Cerradas.",
            action: {
              label: "Ver cerradas",
              onClick: () =>
                router.push(`/conversations/${conversationId}?filter=closed`),
            },
          });
        }}
      />
    </section>
  );
}
