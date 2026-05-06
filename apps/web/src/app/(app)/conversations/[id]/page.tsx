import { notFound } from "next/navigation";
import { ConvList } from "@/components/conversations/ConvList";
import { Thread } from "@/components/conversations/Thread";
import { ContactInfo } from "@/components/conversations/ContactInfo";
import { conversations } from "@/lib/mock";

export default async function ConversationDetailPage(props: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await props.params;
  const exists =
    conversations.some((c) => c.id === id) || id.startsWith("nv-");
  if (!exists) notFound();

  return (
    <div className="flex gap-4 min-w-0 flex-1 h-[calc(100vh-180px)]">
      <ConvList activeId={id} />
      <Thread conversationId={id} />
      <ContactInfo conversationId={id} />
    </div>
  );
}
