/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  Check,
  CheckCheck,
  ChevronLeft,
  Info,
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
import {
  contactDisplayName,
  contactIdentityLabel,
  contactInitials,
} from "@/lib/contact-display";
import { IconButton } from "@/components/ui/IconButton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import { parseApiDate } from "@/lib/dates";
import { useConversationStream } from "@/lib/use-conversation-stream";
import { requestWsTicket } from "../_actions/ws-ticket";
import {
  conversationStatsAction,
  deleteAction,
  loadConversationsAction,
  loadMessagesAction,
} from "../_actions/conversations";
import { MessageComposer } from "./MessageComposer";
import { ConversationActions } from "./ConversationActions";
import { ContactPanel } from "./ContactPanel";
import type {
  ConversationDetail,
  ConversationListItem,
  ConversationStats,
  ConversationStatus,
  DeliveryStatus,
  MessageRead,
  MessageRole,
} from "@/lib/api/conversations";

interface Props {
  conversations: ConversationListItem[];
  initialStats: ConversationStats;
  activeConversation: ConversationDetail;
  activeMessages: MessageRead[];
}

// Tamaño de página del scroll infinito de la barra lateral. Debe coincidir con
// el `size` con que el server hace el fetch inicial en [id]/page.tsx.
const PAGE_SIZE = 20;

type FilterKey = "todas" | "activas" | "escaladas";

// Cada tab mapea a un estado del backend (el filtro es server-side). "todas" no
// filtra → cubre toda la base.
const STATUS_FOR_FILTER: Record<FilterKey, ConversationStatus | undefined> = {
  todas: undefined,
  activas: "abierta",
  escaladas: "takeover",
};

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

const GRADIENTS = ["coral", "blue", "violet", "mint", "amber", "rose"] as const;

function gradientOf(id: number): (typeof GRADIENTS)[number] {
  return GRADIENTS[id % GRADIENTS.length];
}

// Última actividad del hilo (ms). Hay un solo hilo por contacto que se reabre,
// así que `opened_at` es el primer contacto: ordenar por él deja arriba chats
// viejos. Sin mensajes cae a `opened_at`. Mismo criterio que el backend.
function activityTime(c: ConversationListItem): number {
  return parseApiDate(c.last_message_at ?? c.opened_at).getTime();
}

function byActivityDesc(a: ConversationListItem, b: ConversationListItem) {
  return activityTime(b) - activityTime(a) || b.id - a.id;
}

// Picks which conversation to open after the active one is deleted: the most
// recent takeover (an escalation needs attention) else the most recent overall.
function pickNextConversation(
  list: ConversationListItem[],
  excludeId: number,
): ConversationListItem | null {
  const remaining = list
    .filter((c) => c.id !== excludeId)
    .sort(byActivityDesc);
  if (remaining.length === 0) return null;
  return remaining.find((c) => c.status === "takeover") ?? remaining[0];
}

// Fecha de la lista estilo WhatsApp: hora si fue hoy, si no "14 nov".
function fmtActivity(iso: string): string {
  const d = parseApiDate(iso);
  const now = new Date();
  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  return sameDay
    ? d.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString("es-PE", { month: "short", day: "2-digit" });
}

function fmtTime(iso: string | null): string {
  if (!iso) return "";
  return parseApiDate(iso).toLocaleTimeString("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ConversationsClient({
  conversations: initialConversations,
  initialStats,
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

  // ── Layout responsive ──────────────────────────────────────────────────
  // En <md solo cabe un panel: alternamos lista ⟷ hilo. Por defecto mostramos
  // el hilo (estamos viendo una conversación concreta). En <xl la ficha del
  // contacto se abre como overlay desde el botón del hilo.
  const [mobileView, setMobileView] = useState<"list" | "thread">("thread");
  const [contactOpen, setContactOpen] = useState(false);

  // ── Contadores de los tabs (toda la base, no solo lo cargado) ──────────
  const [stats, setStats] = useState(initialStats);
  const refreshStats = useCallback(async () => {
    const res = await conversationStatsAction();
    if (res.ok) setStats(res.data);
  }, []);

  // ── Scroll infinito de la barra lateral ───────────────────────────────
  // `loadedPage` vive en un ref para que el IntersectionObserver siempre lea el
  // valor actual sin recrearse en cada carga.
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(
    initialConversations.length < initialStats.total,
  );
  const loadedPageRef = useRef(1);
  const listRef = useRef<HTMLUListElement | null>(null);
  const sentinelRef = useRef<HTMLLIElement | null>(null);

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    const nextPage = loadedPageRef.current + 1;
    const result = await loadConversationsAction(
      nextPage,
      PAGE_SIZE,
      STATUS_FOR_FILTER[filter],
    );
    if (result.ok) {
      loadedPageRef.current = nextPage;
      setConversations((prev) => {
        const seen = new Set(prev.map((c) => c.id));
        const fresh = result.data.items.filter((c) => !seen.has(c.id));
        return [...prev, ...fresh];
      });
      setHasMore(nextPage < result.data.pages);
    } else {
      // Cortamos el scroll infinito para no reintentar en bucle ante un error.
      setHasMore(false);
      toast.error("No se pudieron cargar más conversaciones", {
        description: result.error,
      });
    }
    setLoadingMore(false);
  }, [loadingMore, hasMore, filter, toast]);

  // Observa un sentinel al final de la lista: cuando entra en viewport (con 200px
  // de margen) pide la siguiente página.
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { root: listRef.current, rootMargin: "200px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadMore]);

  // Cambio de tab → recargamos desde el servidor la página 1 de ese estado, así
  // el filtro cubre TODA la base (no solo lo ya cargado). El primer render usa lo
  // que ya entregó el server (filtro "todas"), por eso lo saltamos.
  const isFirstFilterRun = useRef(true);
  useEffect(() => {
    if (isFirstFilterRun.current) {
      isFirstFilterRun.current = false;
      return;
    }
    let cancelled = false;
    setLoadingMore(true);
    (async () => {
      const res = await loadConversationsAction(
        1,
        PAGE_SIZE,
        STATUS_FOR_FILTER[filter],
      );
      if (cancelled) return;
      if (res.ok) {
        setConversations(res.data.items);
        loadedPageRef.current = 1;
        setHasMore(res.data.page < res.data.pages);
      } else {
        toast.error("No se pudo aplicar el filtro", {
          description: res.error,
        });
      }
      setLoadingMore(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [filter, toast]);

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
          void refreshStats();
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
    setStats(initialStats);
    setFilter("todas");
    // El server reentregó la primera página ("todas") → reiniciamos el cursor del
    // scroll infinito para que vuelva a paginar desde la 2 hacia abajo.
    loadedPageRef.current = 1;
    setHasMore(initialConversations.length < initialStats.total);
  }, [initialConversations, initialStats]);

  // Ids de mensajes ya contados en la lista: un reconnect o un evento repetido
  // no debe inflar `message_count`.
  const countedMsgIdsRef = useRef(new Set<number>());

  // Trae la página 1 del tab actual y la fusiona con lo cargado: actualiza las
  // que ya están y antepone las nuevas (una conversación nueva, o una antigua
  // que no estaba cargada por la paginación y acaba de recibir un mensaje).
  // No usamos router.refresh(): reinicia el tab activo y el scroll infinito.
  const syncFirstPage = useCallback(async () => {
    const res = await loadConversationsAction(
      1,
      PAGE_SIZE,
      STATUS_FOR_FILTER[filter],
    );
    if (!res.ok) return;
    const fresh = new Map(res.data.items.map((c) => [c.id, c]));
    setConversations((prev) => {
      const merged = prev.map((c) => fresh.get(c.id) ?? c);
      const known = new Set(prev.map((c) => c.id));
      const added = res.data.items.filter((c) => !known.has(c.id));
      return [...added, ...merged];
    });
  }, [filter]);

  // Cuántas veces el servidor nos saludó ("hello" llega en cada conexión WS).
  const helloCountRef = useRef(0);

  // El handler se recrea en cada render (el hook guarda siempre el último), así
  // que `conversations`, `filter` y `active` están al día. Decidimos leyendo
  // ese estado y no dentro de un updater de setState: React puede ejecutar los
  // updaters diferidos, y antes eso hacía que una conversación nueva nunca
  // disparara el refresh (el flag se leía antes de que el updater corriera).
  const { connected } = useConversationStream(requestWsTicket, (event) => {
    if (event.type === "hello") {
      helloCountRef.current += 1;
      // Re-conexión (caída de red, deploy de la API, laptop que despierta): los
      // eventos perdidos no se reenvían, así que resincronizamos lista,
      // contadores e hilo abierto. La primera conexión no lo necesita.
      if (helloCountRef.current > 1) {
        void syncFirstPage();
        void refreshStats();
        void loadMessagesAction(active.id).then((res) => {
          if (res.ok) setMessages(res.data);
        });
      }
    } else if (event.type === "message.created") {
      const msg = event.data as MessageRead;
      // Append to the open thread if it belongs to it.
      if (msg.conversation_id === active.id) {
        setMessages((prev) =>
          prev.some((m) => m.id === msg.id) ? prev : [...prev, msg],
        );
      }
      const known = conversations.some(
        (c) => c.id === msg.conversation_id,
      );
      if (!known) {
        // Conversación nueva o fuera de lo cargado: la pedimos al servidor (ya
        // viene con preview y orden correctos) y actualizamos los contadores.
        void syncFirstPage();
        void refreshStats();
        return;
      }
      const firstTime = !countedMsgIdsRef.current.has(msg.id);
      countedMsgIdsRef.current.add(msg.id);
      // Preview + última actividad → el hilo sube al tope de la lista.
      setConversations((prev) =>
        prev.map((c) =>
          c.id === msg.conversation_id
            ? {
                ...c,
                last_message_preview:
                  msg.content.slice(0, 80) +
                  (msg.content.length > 80 ? "..." : ""),
                last_message_at: msg.created_at ?? new Date().toISOString(),
                message_count: c.message_count + (firstTime ? 1 : 0),
              }
            : c,
        ),
      );
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
      // En un tab filtrado ("Activas"/"Escaladas"), la que cambia a otro estado
      // sale de la lista; en "Todas" solo se actualiza el pill.
      const tabStatus = STATUS_FOR_FILTER[filter];
      setConversations((prev) =>
        prev
          .map((c) =>
            c.id === data.conversation_id ? { ...c, status: data.status } : c,
          )
          .filter(
            (c) =>
              !tabStatus ||
              c.id !== data.conversation_id ||
              c.status === tabStatus,
          ),
      );
      // Si entra a este tab (p. ej. se escala estando en "Escaladas"), la traemos.
      if (
        tabStatus === data.status &&
        !conversations.some((c) => c.id === data.conversation_id)
      ) {
        void syncFirstPage();
      }
      void refreshStats();
      if (data.conversation_id === active.id) {
        setActive((prev) => ({ ...prev, status: data.status }));
      }
    } else if (event.type === "conversation.deleted") {
      const data = event.data as { conversation_id: number };
      setConversations((prev) =>
        prev.filter((c) => c.id !== data.conversation_id),
      );
      void refreshStats();
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

  const sortedConversations = useMemo(
    () => [...conversations].sort(byActivityDesc),
    [conversations],
  );

  // Contadores reales por estado (vienen del backend, no de lo cargado).
  const counts = {
    todas: stats.total,
    activas: stats.abierta,
    escaladas: stats.takeover,
  };

  // El estado ya lo filtra el servidor; aquí solo aplicamos la búsqueda por texto
  // sobre lo que está cargado.
  const visibleConversations = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sortedConversations;
    return sortedConversations.filter(
      (c) =>
        (c.display_name?.toLowerCase().includes(q) ?? false) ||
        (c.student_phone?.toLowerCase().includes(q) ?? false) ||
        (c.whatsapp_user_id?.toLowerCase().includes(q) ?? false) ||
        (c.whatsapp_username?.toLowerCase().includes(q) ?? false) ||
        contactIdentityLabel(c).toLowerCase().includes(q) ||
        (c.last_message_preview?.toLowerCase().includes(q) ?? false),
    );
  }, [sortedConversations, query]);

  const activeName = contactDisplayName(active, active.student_profile?.full_name);

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
      <aside
        className={cn(
          "w-full md:w-[330px] shrink-0 min-h-0 md:block",
          mobileView === "list" ? "block" : "hidden",
        )}
      >
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

          <ul ref={listRef} className="flex-1 overflow-auto px-2 pb-2">
            {visibleConversations.length === 0 && !hasMore ? (
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
                        initials={contactInitials(c)}
                        gradient={gradientOf(c.id)}
                        size="md"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <span
                            className="text-[13.5px] font-semibold truncate"
                            title={contactDisplayName(c)}
                          >
                            {contactDisplayName(c)}
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
                            {fmtActivity(c.last_message_at ?? c.opened_at)}
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
            {hasMore && (
              <li
                ref={sentinelRef}
                className="px-3 py-4 text-center text-[11px] text-muted-2"
              >
                {loadingMore ? "Cargando más…" : ""}
              </li>
            )}
          </ul>
        </Card>
      </aside>

      {/* ── Columna 2 · Hilo de chat ──────────────────────────────── */}
      <section
        className={cn(
          "flex-1 min-w-0 min-h-0 md:block",
          mobileView === "thread" ? "block" : "hidden",
        )}
      >
        <Card variant="flush" className="h-full flex flex-col">
          <header className="px-4 sm:px-5 py-4 border-b border-line flex items-center justify-between gap-2 sm:gap-3">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              {/* Volver a la lista (solo móvil, donde solo cabe un panel) */}
              <button
                type="button"
                onClick={() => setMobileView("list")}
                aria-label="Volver a la lista"
                className="md:hidden shrink-0 -ml-1 w-9 h-9 rounded-full flex items-center justify-center text-muted hover:text-fg hover:bg-bg-2 transition-colors"
              >
                <ChevronLeft size={20} strokeWidth={2} />
              </button>
              <Avatar
                initials={contactInitials(active, active.student_profile?.full_name)}
                gradient={gradientOf(active.id)}
                size="md"
              />
              <div className="min-w-0">
                <div
                  className="text-[15px] font-bold tracking-[-0.3px] truncate"
                  title={activeName}
                >
                  {activeName}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <Pill tone={STATUS_TONE[active.status]}>
                    {STATUS_LABEL[active.status]}
                  </Pill>
                  <span
                    className="text-[11px] text-muted font-mono min-w-0 truncate"
                    title={contactIdentityLabel(active)}
                  >
                    {contactIdentityLabel(active)}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              {/* Abrir ficha del contacto como overlay (cuando no es panel fijo) */}
              <button
                type="button"
                onClick={() => setContactOpen(true)}
                aria-label="Ver ficha del contacto"
                className="xl:hidden w-9 h-9 rounded-full flex items-center justify-center text-muted hover:text-fg hover:bg-bg-2 transition-colors"
              >
                <Info size={18} strokeWidth={2} />
              </button>
              <ConversationActions
                conversationId={active.id}
                status={active.status}
              />
            </div>
          </header>

          <div
            ref={threadRef}
            className="flex-1 overflow-auto px-3 sm:px-6 py-4 sm:py-5 space-y-4 bg-bg"
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
      <ContactPanel
        conversation={active}
        onChange={handleConversationChange}
        open={contactOpen}
        onClose={() => setContactOpen(false)}
      />

      {deleteTarget && (
        <ConfirmDialog
          open
          onOpenChange={(v) => !v && setDeleteTarget(null)}
          title="Eliminar conversación"
          description={`Se borrará la conversación con ${
            contactDisplayName(deleteTarget)
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
        <div className="flex max-w-[88%] sm:max-w-[82%] items-center gap-1">
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
      <div className="flex max-w-[88%] sm:max-w-[82%] items-center gap-1">
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
