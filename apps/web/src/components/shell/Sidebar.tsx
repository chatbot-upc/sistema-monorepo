"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { ChevronUp, User, LogOut } from "lucide-react";
import { cn } from "@/lib/cn";
import { Avatar } from "@/components/ui/Avatar";
import { Dropdown } from "@/components/ui/Dropdown";
import { useToast } from "@/components/ui/ToastProvider";
import { NAV } from "./nav";

interface SidebarProps {
  conversationsCount?: number;
}

export function Sidebar({ conversationsCount }: SidebarProps) {
  const pathname = usePathname();
  const { toast } = useToast();

  return (
    <aside className="hidden md:flex bg-surface rounded-3xl flex-col gap-1 w-[260px] shrink-0 sticky top-4 h-[calc(100vh-32px)] px-4 py-6">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-3 pt-1 pb-6">
        <div className="w-7 h-7 rounded-lg bg-primary text-white flex items-center justify-center relative font-extrabold text-sm">
          <span className="absolute w-3 h-0.5 bg-white rounded-sm" />
          <span className="absolute w-0.5 h-3 bg-white rounded-sm" />
        </div>
        <div className="font-bold text-lg tracking-[-0.3px]">
          UPC<span className="text-primary">Bot</span>
        </div>
      </div>

      {/* Nav */}
      {NAV.map((item) => {
        const Icon = item.icon;
        const href = item.href.split("?")[0];
        const isActive = pathname === href || pathname.startsWith(`${href}/`);
        const badge =
          item.href === "/conversations" ? conversationsCount : item.badge;
        return (
          <Link
            key={item.label}
            href={item.href}
            className={cn(
              "flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-[14px] transition-all relative",
              isActive
                ? "bg-bg-2 text-fg font-semibold"
                : "text-muted hover:bg-bg-2 hover:text-fg-2 font-medium"
            )}
          >
            <Icon size={18} strokeWidth={1.75} className="shrink-0" />
            {item.label}
            {badge != null && badge > 0 && (
              <span className="ml-auto bg-primary text-white font-mono text-[10px] px-2 py-0.5 rounded-full font-medium">
                {badge}
              </span>
            )}
          </Link>
        );
      })}

      <div className="flex-1" />

      {/* User block */}
      <div className="border-t border-line">
        <Dropdown align="start" side="top">
          <Dropdown.Trigger>
            <button
              type="button"
              className="w-full flex items-center gap-3 px-3 py-4 rounded-xl hover:bg-bg-2 transition-colors cursor-pointer text-left"
            >
              <Avatar initials="RL" gradient="coral" />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-semibold">Renzo Lenes</div>
                <div className="text-[11px] text-muted font-mono">ID: 72630284</div>
              </div>
              <ChevronUp size={14} className="text-muted shrink-0" strokeWidth={2} />
            </button>
          </Dropdown.Trigger>
          <Dropdown.Content minWidth={228}>
            <Dropdown.Label>Cuenta</Dropdown.Label>
            <Dropdown.Item
              icon={<User size={14} strokeWidth={2} />}
              onSelect={() => toast.info("Mi perfil — próximamente")}
            >
              Mi perfil
            </Dropdown.Item>
            <Dropdown.Separator />
            <Dropdown.Item
              destructive
              icon={<LogOut size={14} strokeWidth={2} />}
              onSelect={() => {
                // Antes solo navegaba a /login y la cookie de sesión seguía viva.
                void signOut({ redirectTo: "/login" });
              }}
            >
              Cerrar sesión
            </Dropdown.Item>
          </Dropdown.Content>
        </Dropdown>
      </div>
    </aside>
  );
}
