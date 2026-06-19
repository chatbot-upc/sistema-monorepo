import { redirect } from "next/navigation";
import { fetchConversations } from "@/lib/api/conversations";

export const dynamic = "force-dynamic";

export default async function ConversationsPage() {
  const page = await fetchConversations({ size: 20 });
  if (page.items.length === 0) {
    // No conversations yet — show the empty list scaffold.
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-muted">
        Aún no hay conversaciones. Espera al primer WhatsApp del estudiante.
      </div>
    );
  }
  // Prefer the most recent takeover so an escalation is the first thing the
  // admin sees when they walk in.
  const takeover = page.items.find((c) => c.status === "takeover");
  const target = takeover ?? page.items[0];
  redirect(`/conversations/${target.id}`);
}
