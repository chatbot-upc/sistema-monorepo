/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, MessageCircle, Phone, Wifi, WifiOff } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { cn } from "@/lib/cn";
import { useConversationStream } from "@/lib/use-conversation-stream";
import { requestWsTicket } from "../_actions/ws-ticket";
import { MessageComposer } from "./MessageComposer";
import { ConversationActions } from "./ConversationActions";
import type {
  ConversationDetail,
  ConversationListItem,
  ConversationStatus,
  MessageRead,
} from "@/lib/api/conversations";

interface Props {
  conversations: ConversationListItem[];
  activeConversation: ConversationDetail;
  activeMessages: MessageRead[];
}

const STATUS_TONE: Record<
  ConversationStatus,
  "active" | "pending" | "closed" | "escalated"
> = {
  abierta: "active",
  cerrada: "closed",
  takeover: "escalated",
};

const STATUS_LABEL: Record<ConversationStatus, string> = {
  abierta: "Abierta",
  cerrada: "Cerrada",
  takeover: "Derivada",
};

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("es-PE", {
    month: "short",
    day: "2-digit",
  });
}

export function ConversationsClient({
  conversations: initialConversations,
  activeConversation,
  activeMessages: initialMessages,
}: Props) {
  const router = useRouter();
  const [conversations, setConversations] = useState(initialConversations);
  const [messages, setMessages] = useState<MessageRead[]>(initialMessages);
  const [active, setActive] = useState(activeConversation);
  const threadRef = useRef<HTMLDivElement | null>(null);

  // Reset state when the route changes to a different conversation. The
  // <ConversationsClient key={detail.id}> in [id]/page.tsx forces a remount
  // on id change, so we only need to sync when the sidebar list changes.
  useEffect(() => {
    setConversations(initialConversations);
  }, [initialConversations]);

  const { connected } = useConversationStream(requestWsTicket, (event) => {
    if (event.type === "message.created") {
      const msg = event.data as MessageRead;
      // Append to the open thread if it belongs to it.
      if (msg.conversation_id === active.id) {
        setMessages((prev) =>
          prev.some((m) => m.id === msg.id) ? prev : [...prev, msg],
        );
      }
      // Patch the sidebar preview + ordering.
      let isUnknownConversation = false;
      setConversations((prev) => {
        const idx = prev.findIndex((c) => c.id === msg.conversation_id);
        if (idx === -1) {
          // New conversation — refresh server data outside this setter to
          // avoid triggering Router setState during render.
          isUnknownConversation = true;
          return prev;
        }
        const next = [...prev];
        next[idx] = {
          ...next[idx],
          last_message_preview:
            msg.content.slice(0, 80) + (msg.content.length > 80 ? "..." : ""),
          message_count: next[idx].message_count + 1,
        };
        return next;
      });
      if (isUnknownConversation) {
        router.refresh();
      }
    } else if (event.type === "conversation.status_changed") {
      const data = event.data as {
        conversation_id: number;
        status: ConversationStatus;
      };
      setConversations((prev) =>
        prev.map((c) =>
          c.id === data.conversation_id ? { ...c, status: data.status } : c,
        ),
      );
      if (data.conversation_id === active.id) {
        setActive((prev) => ({ ...prev, status: data.status }));
      }
    } else if (event.type === "conversation.deleted") {
      const data = event.data as { conversation_id: number };
      setConversations((prev) =>
        prev.filter((c) => c.id !== data.conversation_id),
      );
      // Si borraron la que estoy viendo (desde otra pestaña), salgo a la lista.
      if (data.conversation_id === active.id) {
        router.push("/conversations");
      }
    }
  });

  // Auto-scroll to latest message after the thread re-renders.
  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight;
    }
  }, [messages]);

  const sortedConversations = useMemo(() => {
    return [...conversations].sort((a, b) => {
      const ta = new Date(a.opened_at).getTime();
      const tb = new Date(b.opened_at).getTime();
      return tb - ta;
    });
  }, [conversations]);

  return (
    <div className="flex gap-4 min-w-0 h-[calc(100dvh-96px)]">
      {/* Sidebar — conversation list */}
      <aside className="w-[300px] shrink-0 flex flex-col gap-3 overflow-hidden min-h-0">
        <header className="flex items-center justify-between px-1">
          <h2 className="text-[15px] font-semibold tracking-[-0.3px]">
            Conversaciones
          </h2>
          <div
            className={cn(
              "flex items-center gap-1 text-[11px] font-mono",
              connected ? "text-success" : "text-muted-2",
            )}
            title={connected ? "Conectado en tiempo real" : "Sin conexión"}
          >
            {connected ? (
              <Wifi size={12} strokeWidth={2.5} />
            ) : (
              <WifiOff size={12} strokeWidth={2.5} />
            )}
            <span>{connected ? "live" : "offline"}</span>
          </div>
        </header>
        <Card variant="flush" className="flex-1 overflow-auto p-0">
          <ul className="flex flex-col">
            {sortedConversations.map((c) => {
              const isActive = c.id === active.id;
              return (
                <li key={c.id}>
                  <Link
                    href={`/conversations/${c.id}`}
                    className={cn(
                      "flex flex-col gap-1 px-4 py-3 border-b border-line hover:bg-bg-2 transition-colors",
                      isActive && "bg-bg-2",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[13px] font-semibold truncate">
                        {c.display_name ?? c.student_phone}
                      </span>
                      <Pill tone={STATUS_TONE[c.status]}>
                        {STATUS_LABEL[c.status]}
                      </Pill>
                    </div>
                    <div className="flex items-center justify-between gap-2 text-[11px] text-muted font-mono">
                      <span className="truncate">
                        {c.last_message_preview ?? "(sin mensajes)"}
                      </span>
                      <span className="shrink-0">{fmtDate(c.opened_at)}</span>
                    </div>
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>
      </aside>

      {/* Thread */}
      <section className="flex-1 min-w-0 flex flex-col gap-3 min-h-0">
        <header className="flex items-center justify-between px-1">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-blue-soft text-blue flex items-center justify-center">
              <MessageCircle size={16} strokeWidth={2} />
            </div>
            <div>
              <div className="text-[15px] font-semibold tracking-[-0.3px]">
                {active.display_name ?? active.student_phone}
              </div>
              <div className="text-[11px] text-muted font-mono flex items-center gap-1">
                <Phone size={11} strokeWidth={2} />
                {active.student_phone}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ConversationActions
              conversationId={active.id}
              status={active.status}
              onDeleted={() => {
                setConversations((prev) =>
                  prev.filter((c) => c.id !== active.id),
                );
                router.push("/conversations");
              }}
            />
            <Pill tone={STATUS_TONE[active.status]}>
              {STATUS_LABEL[active.status]}
            </Pill>
          </div>
        </header>

        <Card variant="flush" className="flex-1 overflow-hidden flex flex-col">
          <div ref={threadRef} className="flex-1 overflow-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted text-sm py-12">
                Aún no hay mensajes en esta conversación.
              </div>
            ) : (
              messages.map((m) => <Bubble key={m.id} msg={m} />)
            )}
          </div>
          <MessageComposer conversationId={active.id} status={active.status} />
        </Card>
      </section>

      {/* Sidebar derecho — info del estudiante */}
      <aside className="w-[260px] shrink-0 min-h-0 overflow-auto">
        <Card className="p-5 flex flex-col gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
              Estudiante
            </div>
            <div className="text-[15px] font-semibold mt-1">
              {active.display_name ?? "—"}
            </div>
            <div className="text-[12px] text-muted font-mono mt-1">
              {active.student_phone}
            </div>
          </div>
          <div className="border-t border-line pt-4">
            <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
              Estado
            </div>
            <div className="mt-2">
              <Pill tone={STATUS_TONE[active.status]}>
                {STATUS_LABEL[active.status]}
              </Pill>
            </div>
          </div>
          <div className="border-t border-line pt-4">
            <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
              Abierta
            </div>
            <div className="text-[12px] font-mono mt-1">
              {new Date(active.opened_at).toLocaleString("es-PE")}
            </div>
          </div>
          {active.closed_at && (
            <div className="border-t border-line pt-4">
              <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
                Cerrada
              </div>
              <div className="text-[12px] font-mono mt-1 flex items-center gap-1">
                <CheckCircle2 size={11} className="text-success" />
                {new Date(active.closed_at).toLocaleString("es-PE")}
              </div>
            </div>
          )}
        </Card>
      </aside>
    </div>
  );
}

function Bubble({ msg }: { msg: MessageRead }) {
  const isStudent = msg.role === "student";
  const alignment = isStudent ? "items-start" : "items-end";
  const bubbleClass = isStudent
    ? "bg-surface-2 text-fg"
    : msg.role === "admin"
      ? "bg-amber-soft text-amber-fg"
      : "bg-primary text-white";

  return (
    <div className={cn("flex flex-col gap-1", alignment)}>
      <div
        className={cn(
          "max-w-[75%] rounded-2xl px-4 py-2.5 whitespace-pre-wrap text-[13px] leading-relaxed shadow-sm",
          bubbleClass,
        )}
      >
        {msg.content}
      </div>
      <div className="flex items-center gap-2 text-[10px] text-muted font-mono">
        <span>{msg.role}</span>
        <span>·</span>
        <span>{fmtTime(msg.created_at)}</span>
        {msg.latency_ms !== null && msg.latency_ms !== undefined && (
          <>
            <span>·</span>
            <span>{(msg.latency_ms / 1000).toFixed(1)}s</span>
          </>
        )}
      </div>
    </div>
  );
}
