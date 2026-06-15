/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  Check,
  CheckCheck,
  Plus,
  Reply,
  Search,
  Star,
  Trash2,
  User,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { Avatar } from "@/components/ui/Avatar";
import { IconButton } from "@/components/ui/IconButton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import { parseApiDate } from "@/lib/dates";
import { useConversationStream } from "@/lib/use-conversation-stream";
import { requestWsTicket } from "../_actions/ws-ticket";
import { deleteAction } from "../_actions/conversations";
import { MessageComposer } from "./MessageComposer";
import { ConversationActions } from "./ConversationActions";
import { ContactPanel } from "./ContactPanel";
import type {
  ConversationDetail,
  ConversationListItem,
  ConversationStatus,
  DeliveryStatus,
  MessageRead,
  MessageRole,
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
  takeover: "Escalada",
};

type FilterKey = "todas" | "activas" | "escaladas";

const GRADIENTS = ["coral", "blue", "violet", "mint", "amber", "rose"] as const;

function gradientOf(id: number): (typeof GRADIENTS)[number] {
  return GRADIENTS[id % GRADIENTS.length];
}

function initialsOf(name: string | null, phone: string): string {
  const src = name?.trim();
  if (src) {
    const parts = src.split(/\s+/);
    return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
  }
  return phone.replace(/\D/g, "").slice(-2);
}

// Picks which conversation to open after the active one is deleted: the most
// recent takeover (an escalation needs attention) else the most recent overall.
function pickNextConversation(
  list: ConversationListItem[],
  excludeId: number,
): ConversationListItem | null {
  const remaining = [...list]
    .filter((c) => c.id !== excludeId)
    .sort(
      (a, b) =>
        new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime(),
    );
  if (remaining.length === 0) return null;
  return remaining.find((c) => c.status === "takeover") ?? remaining[0];
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return parseApiDate(iso).toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function fmtDate(iso: string | null): string {
  if (!iso) return "";
  return parseApiDate(iso).toLocaleDateString("es-PE", {
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
  const { toast } = useToast();
  const [conversations, setConversations] = useState(initialConversations);
  const [messages, setMessages] = useState<MessageRead[]>(initialMessages);
  const [active, setActive] = useState(activeConversation);
  const [deleteTarget, setDeleteTarget] = useState<ConversationListItem | null>(
    null,
  );
  const [deleting, startDelete] = useTransition();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<FilterKey>("todas");
  const [replyingTo, setReplyingTo] = useState<MessageRead | null>(null);
  const threadRef = useRef<HTMLDivElement | null>(null);

  // After deleting the active conversation, jump straight to the next sibling
  // (single navigation) instead of bouncing through /conversations, which
  // re-fetches and redirects — that double hop is what flashes on screen.
  const goAfterDeletingActive = (deletedId: number) => {
    const next = pickNextConversation(conversations, deletedId);
    router.push(next ? `/conversations/${next.id}` : "/conversations");
  };

  const handleDelete = (target: ConversationListItem) =>
    new Promise<void>((resolve, reject) => {
      startDelete(async () => {
        const result = await deleteAction(target.id);
        if (result.ok) {
          toast.success("Conversación eliminada");
          setConversations((prev) => prev.filter((c) => c.id !== target.id));
          setDeleteTarget(null);
          if (target.id === active.id) {
            goAfterDeletingActive(target.id);
          }
          resolve();
        } else {
          toast.error("No se pudo eliminar", { description: result.error });
          reject(new Error(result.error));
        }
      });
    });

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
    } else if (event.type === "message.status_changed") {
      const data = event.data as {
        message_id: number;
        conversation_id: number;
        delivery_status: DeliveryStatus;
      };
      if (data.conversation_id === active.id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === data.message_id
              ? { ...m, delivery_status: data.delivery_status }
              : m,
          ),
        );
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
      // Si borraron la que estoy viendo (desde otra pestaña / otro admin),
      // salto directo a la siguiente conversación.
      if (data.conversation_id === active.id) {
        goAfterDeletingActive(data.conversation_id);
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
    return [...conversations].sort(
      (a, b) =>
        new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime(),
    );
  }, [conversations]);

  const counts = useMemo(
    () => ({
      todas: conversations.length,
      activas: conversations.filter((c) => c.status === "abierta").length,
      escaladas: conversations.filter((c) => c.status === "takeover").length,
    }),
    [conversations],
  );

  const visibleConversations = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sortedConversations.filter((c) => {
      if (filter === "activas" && c.status !== "abierta") return false;
      if (filter === "escaladas" && c.status !== "takeover") return false;
      if (!q) return true;
      return (
        (c.display_name?.toLowerCase().includes(q) ?? false) ||
        c.student_phone.toLowerCase().includes(q) ||
        (c.last_message_preview?.toLowerCase().includes(q) ?? false)
      );
    });
  }, [sortedConversations, filter, query]);

  const activeName =
    active.student_profile?.full_name ??
    active.display_name ??
    active.student_phone;

  // Las mutaciones de la ficha (destacar/correo/etiquetas) devuelven el detalle
  // actualizado; sincronizamos el panel y, para `starred`, también la lista.
  const handleConversationChange = (updated: ConversationDetail) => {
    setActive(updated);
    setConversations((prev) =>
      prev.map((c) =>
        c.id === updated.id ? { ...c, starred: updated.starred } : c,
      ),
    );
  };

  return (
    <div className="flex gap-4 min-w-0 h-[calc(100dvh-96px)]">
      {/* ── Columna 1 · Lista de conversaciones ───────────────────── */}
      <aside className="w-[330px] shrink-0 min-h-0">
        <Card variant="flush" className="h-full flex flex-col">
          <header className="px-5 pt-5 pb-3 flex items-center justify-between">
            <h2 className="text-[19px] font-bold tracking-[-0.4px]">Mensajes</h2>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex items-center gap-1 text-[10px] font-mono",
                  connected ? "text-success" : "text-muted-2",
                )}
                title={connected ? "Conectado en tiempo real" : "Sin conexión"}
              >
                {connected ? (
                  <Wifi size={11} strokeWidth={2.5} />
                ) : (
                  <WifiOff size={11} strokeWidth={2.5} />
                )}
              </span>
              <IconButton
                variant="ghost"
                size="sm"
                onClick={() => toast.info("Nueva conversación — próximamente")}
                aria-label="Nueva conversación"
              >
                <Plus size={16} strokeWidth={2.5} />
              </IconButton>
            </div>
          </header>

          {/* Buscador */}
          <div className="px-5 pb-3">
            <div className="relative">
              <Search
                size={15}
                strokeWidth={2}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted pointer-events-none"
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Buscar conversaciones"
                className="w-full rounded-xl bg-surface-2 border border-line pl-9 pr-3 py-2 text-[13px] placeholder:text-muted focus-visible:border-primary"
              />
            </div>
          </div>

          {/* Filtros */}
          <div className="px-5 pb-3 flex items-center gap-2">
            <FilterTab
              active={filter === "todas"}
              onClick={() => setFilter("todas")}
              label="Todas"
              count={counts.todas}
            />
            <FilterTab
              active={filter === "activas"}
              onClick={() => setFilter("activas")}
              label="Activas"
              count={counts.activas}
            />
            <FilterTab
              active={filter === "escaladas"}
              onClick={() => setFilter("escaladas")}
              label="Escaladas"
              count={counts.escaladas}
              tone="danger"
            />
          </div>

          <ul className="flex-1 overflow-auto px-2 pb-2">
            {visibleConversations.length === 0 ? (
              <li className="px-3 py-8 text-center text-[12px] text-muted">
                Sin resultados.
              </li>
            ) : (
              visibleConversations.map((c) => {
                const isActive = c.id === active.id;
                const isEscalated = c.status === "takeover";
                return (
                  <li key={c.id} className="group relative">
                    <Link
                      href={`/conversations/${c.id}`}
                      className={cn(
                        "flex items-center gap-3 px-3 py-3 rounded-2xl transition-colors",
                        isActive ? "bg-bg-2" : "hover:bg-bg-2",
                      )}
                    >
                      <Avatar
                        initials={initialsOf(c.display_name, c.student_phone)}
                        gradient={gradientOf(c.id)}
                        size="md"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-[13.5px] font-semibold truncate">
                            {c.display_name ?? c.student_phone}
                          </span>
                          <span className="shrink-0 flex items-center gap-1 text-[11px] text-muted font-mono">
                            {c.starred && (
                              <Star
                                size={11}
                                strokeWidth={2}
                                className="text-amber"
                                fill="currentColor"
                              />
                            )}
                            {fmtDate(c.opened_at)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-2 mt-0.5">
                          <span className="truncate text-[12px] text-muted">
                            {c.last_message_preview ?? "(sin mensajes)"}
                          </span>
                          {isEscalated && (
                            <span className="shrink-0 w-2 h-2 rounded-full bg-primary group-hover:opacity-0 transition-opacity" />
                          )}
                        </div>
                      </div>
                    </Link>
                    <IconButton
                      variant="ghost"
                      size="sm"
                      disabled={deleting}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setDeleteTarget(c);
                      }}
                      aria-label="Eliminar conversación"
                      className="absolute right-3 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-muted hover:text-danger transition-opacity"
                    >
                      <Trash2 size={15} strokeWidth={2} />
                    </IconButton>
                  </li>
                );
              })
            )}
          </ul>
        </Card>
      </aside>

      {/* ── Columna 2 · Hilo de chat ──────────────────────────────── */}
      <section className="flex-1 min-w-0 min-h-0">
        <Card variant="flush" className="h-full flex flex-col">
          <header className="px-5 py-4 border-b border-line flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <Avatar
                initials={initialsOf(
                  active.student_profile?.full_name ?? active.display_name,
                  active.student_phone,
                )}
                gradient={gradientOf(active.id)}
                size="md"
              />
              <div className="min-w-0">
                <div className="text-[15px] font-bold tracking-[-0.3px] truncate">
                  {activeName}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <Pill tone={STATUS_TONE[active.status]}>
                    {STATUS_LABEL[active.status]}
                  </Pill>
                  <span className="text-[11px] text-muted font-mono">
                    {active.student_phone}
                  </span>
                </div>
              </div>
            </div>
            <ConversationActions
              conversationId={active.id}
              status={active.status}
            />
          </header>

          <div
            ref={threadRef}
            className="flex-1 overflow-auto px-6 py-5 space-y-4 bg-bg"
          >
            {messages.length === 0 ? (
              <div className="text-center text-muted text-sm py-12">
                Aún no hay mensajes en esta conversación.
              </div>
            ) : (
              messages.map((m) => (
                <Bubble key={m.id} msg={m} onReply={setReplyingTo} />
              ))
            )}
          </div>
          <MessageComposer
            conversationId={active.id}
            status={active.status}
            replyingTo={replyingTo}
            onCancelReply={() => setReplyingTo(null)}
          />
        </Card>
      </section>

      {/* ── Columna 3 · Ficha del contacto ────────────────────────── */}
      <ContactPanel conversation={active} onChange={handleConversationChange} />

      {deleteTarget && (
        <ConfirmDialog
          open
          onOpenChange={(v) => !v && setDeleteTarget(null)}
          title="Eliminar conversación"
          description={`Se borrará la conversación con ${
            deleteTarget.display_name ?? deleteTarget.student_phone
          } y todos sus mensajes de forma permanente. Esta acción no se puede deshacer.`}
          confirmLabel="Eliminar"
          variant="destructive"
          onConfirm={() => handleDelete(deleteTarget)}
        />
      )}
    </div>
  );
}

function FilterTab({
  active,
  onClick,
  label,
  count,
  tone = "default",
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  tone?: "default" | "danger";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12px] font-semibold transition-colors",
        active
          ? "bg-ink text-white"
          : "text-muted hover:bg-bg-2 hover:text-fg-2",
      )}
    >
      {label}
      <span
        className={cn(
          "font-mono text-[10px]",
          active
            ? "text-white/70"
            : tone === "danger"
              ? "text-primary"
              : "text-muted-2",
        )}
      >
        {count}
      </span>
    </button>
  );
}

const ROLE_LABEL: Record<MessageRole, string> = {
  student: "Estudiante",
  bot: "Remi",
  admin: "Admin UPC",
};

// Bloque "respondiendo a:" pintado dentro de la burbuja cuando el mensaje cita
// a otro. `onSurface` ajusta el contraste sobre burbujas oscuras (admin).
function QuotedPreview({
  quoted,
  onSurface,
}: {
  quoted: NonNullable<MessageRead["quoted"]>;
  onSurface?: boolean;
}) {
  return (
    <div
      className={cn(
        "mb-1.5 rounded-md border-l-2 pl-2 py-0.5",
        onSurface
          ? "border-white/60 bg-white/10"
          : "border-primary/60 bg-bg-2/60",
      )}
    >
      <div
        className={cn(
          "text-[10px] font-semibold",
          onSurface ? "text-white/80" : "text-primary",
        )}
      >
        {ROLE_LABEL[quoted.role]}
      </div>
      <div
        className={cn(
          "truncate text-[11.5px]",
          onSurface ? "text-white/70" : "text-muted",
        )}
      >
        {quoted.content}
      </div>
    </div>
  );
}

function ReplyButton({
  onClick,
  className,
}: {
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Responder a este mensaje"
      title="Responder"
      className={cn(
        "shrink-0 self-center rounded-full p-1.5 text-muted opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:bg-bg-2 hover:text-primary transition-opacity",
        className,
      )}
    >
      <Reply size={14} strokeWidth={2.5} />
    </button>
  );
}

function Bubble({
  msg,
  onReply,
}: {
  msg: MessageRead;
  onReply: (msg: MessageRead) => void;
}) {
  const isAdmin = msg.role === "admin";
  const isBot = msg.role === "bot";
  const isStudent = msg.role === "student";
  const latency =
    msg.latency_ms !== null && msg.latency_ms !== undefined
      ? `${(msg.latency_ms / 1000).toFixed(1)}s`
      : null;

  // El estudiante (entrante) va a la izquierda; el bot y el admin (salientes)
  // van a la derecha.
  if (isStudent) {
    return (
      <div className="group flex flex-col items-start gap-1">
        <div className="flex max-w-[82%] items-center gap-1">
          <div className="min-w-0 rounded-2xl rounded-bl-md bg-surface border border-line text-fg px-4 py-3 shadow-sm">
            {msg.quoted && <QuotedPreview quoted={msg.quoted} />}
            <div className="whitespace-pre-wrap text-[13px] leading-relaxed">
              {msg.content}
            </div>
          </div>
          <ReplyButton onClick={() => onReply(msg)} />
        </div>
        <span className="text-[10px] text-muted font-mono pl-1">
          {fmtTime(msg.created_at)} · Estudiante
        </span>
      </div>
    );
  }

  return (
    <div className="group flex flex-col items-end gap-1">
      <div className="flex max-w-[82%] items-center gap-1">
        <ReplyButton onClick={() => onReply(msg)} />
        <div
          className={cn(
            "min-w-0 rounded-2xl rounded-br-md px-4 py-3 shadow-sm",
            isAdmin
              ? "bg-primary text-white"
              : "bg-blue-soft/50 border border-blue-soft text-fg",
          )}
        >
          {msg.quoted && <QuotedPreview quoted={msg.quoted} onSurface={isAdmin} />}
          <div
            className={cn(
              "flex items-center gap-1.5 text-[11px] font-semibold mb-1",
              isAdmin ? "text-white/85" : "text-blue",
            )}
          >
            {isAdmin ? (
              <User size={12} strokeWidth={2.5} />
            ) : (
              <Bot size={13} strokeWidth={2.5} />
            )}
            {isAdmin ? "Admin UPC" : "Remi"}
          </div>
          <div className="whitespace-pre-wrap text-[13px] leading-relaxed">
            {msg.content}
          </div>
        </div>
      </div>
      <span className="flex items-center gap-1 text-[10px] text-muted font-mono pr-1">
        <span>
          {fmtTime(msg.created_at)} · {isAdmin ? "Admin UPC" : "Remi"}
          {isBot && latency ? ` · ${latency}` : ""}
        </span>
        <DeliveryTicks status={msg.delivery_status} />
      </span>
    </div>
  );
}

// Checks de entrega del saliente (estilo WhatsApp): ✓ enviado, ✓✓ entregado,
// ✓✓ azul leído, ! fallido. Sin estado → no pinta nada.
function DeliveryTicks({ status }: { status: DeliveryStatus | null }) {
  if (!status) return null;
  if (status === "failed") {
    return (
      <span title="No entregado" className="text-danger font-bold">
        !
      </span>
    );
  }
  if (status === "read") {
    return (
      <CheckCheck
        size={13}
        strokeWidth={2.5}
        className="text-blue"
        aria-label="Leído"
      />
    );
  }
  if (status === "delivered") {
    return (
      <CheckCheck
        size={13}
        strokeWidth={2.5}
        className="text-muted"
        aria-label="Entregado"
      />
    );
  }
  return (
    <Check
      size={13}
      strokeWidth={2.5}
      className="text-muted"
      aria-label="Enviado"
    />
  );
}
