import { notFound } from "next/navigation";
import {
  fetchConversation,
  fetchConversations,
  fetchConversationStats,
  fetchMessages,
  type ConversationDetail,
  type ConversationListItem,
  type MessageRead,
} from "@/lib/api/conversations";
import { ConversationsClient } from "../_components/ConversationsClient";

export const dynamic = "force-dynamic";

export default async function ConversationDetailPage(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  const conversationId = Number.parseInt(id, 10);
  if (!Number.isFinite(conversationId) || conversationId <= 0) {
    notFound();
  }

  // Parallel fetch: list (sidebar) + stats + detail + messages. La barra lateral
  // arranca con la primera página (20); el resto llega vía scroll infinito. Los
  // contadores de los tabs salen de stats (toda la base, no solo lo cargado).
  const [listPage, stats, detail, messagesPage] = await Promise.all([
    fetchConversations({ size: 20 }),
    fetchConversationStats().catch(() => null),
    fetchConversation(conversationId).catch(() => null),
    fetchMessages(conversationId).catch(() => null),
  ]);

  if (!detail || !messagesPage) notFound();

  return (
    <ConversationsClient
      key={detail.id}
      conversations={listPage.items as ConversationListItem[]}
      initialStats={
        stats ?? {
          total: listPage.total,
          abierta: 0,
          cerrada: 0,
          takeover: 0,
        }
      }
      activeConversation={detail as ConversationDetail}
      activeMessages={messagesPage.items as MessageRead[]}
    />
  );
}
