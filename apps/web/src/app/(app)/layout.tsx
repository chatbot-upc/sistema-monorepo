import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-bg-2 p-4 gap-4">
      <Sidebar />
      <main className="flex-1 min-w-0 flex flex-col gap-5">
        <Topbar />
        {children}
      </main>
    </div>
  );
}
