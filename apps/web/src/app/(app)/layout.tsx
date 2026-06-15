import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { fetchConversations } from "@/lib/api/conversations";

import { FcmRegisterClient } from "./_components/FcmRegisterClient";

export const dynamic = "force-dynamic";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Total real de conversaciones para el badge del sidebar (size=1: solo el total).
  const conversationsCount = await fetchConversations({ size: 1 })
    .then((p) => p.total)
    .catch(() => undefined);

  return (
    <div className="flex min-h-screen bg-bg-2 p-4 gap-4">
      <Sidebar conversationsCount={conversationsCount} />
      <main className="flex-1 min-w-0 flex flex-col gap-5">
        <Topbar />
        {children}
      </main>
      <FcmRegisterClient />
    </div>
  );
}
