import { redirect } from "next/navigation";
import { conversations } from "@/lib/mock";

export default function ConversationsPage() {
  // Default to first escalated conversation
  const first = conversations.find((c) => c.status === "escalated") ?? conversations[0];
  redirect(`/conversations/${first.id}`);
}
