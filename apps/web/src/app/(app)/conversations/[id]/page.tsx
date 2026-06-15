import { notFound } from "next/navigation";
import {
  fetchConversation,
  fetchConversations,
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

  // Parallel fetch: list (sidebar) + detail + messages.
  const [listPage, detail, messagesPage] = await Promise.all([
    fetchConversations({ size: 50 }),
    fetchConversation(conversationId).catch(() => null),
    fetchMessages(conversationId).catch(() => null),
  ]);

  if (!detail || !messagesPage) notFound();

  return (
    <ConversationsClient
      key={detail.id}
      conversations={listPage.items as ConversationListItem[]}
      activeConversation={detail as ConversationDetail}
      activeMessages={messagesPage.items as MessageRead[]}
    />
  );
}
