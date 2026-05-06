"use client";

import Link from "next/link";
import { Bell } from "lucide-react";
import { IconButton } from "@/components/ui/IconButton";
import { Dropdown } from "@/components/ui/Dropdown";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import { useNotifications } from "./notifications/useNotifications";
import { NotificationItem } from "./notifications/NotificationItem";

export function NotificationsDropdown() {
  const { items, tab, setTab, unreadCount, visible, markRead, markAllRead } =
    useNotifications();
  const { toast } = useToast();

  return (
    <Dropdown align="end" side="bottom">
      <Dropdown.Trigger>
        <IconButton
          variant="surface"
          className="relative !w-11 !h-11"
          aria-label={`Notificaciones${unreadCount ? ` (${unreadCount} sin leer)` : ""}`}
        >
          <Bell size={17} strokeWidth={1.75} />
          {unreadCount > 0 && (
            <span className="absolute top-3 right-3.5 w-2 h-2 bg-primary border-2 border-surface rounded-full" />
          )}
        </IconButton>
      </Dropdown.Trigger>
      <Dropdown.Content className="!p-0 w-[360px]" minWidth={360}>
        <div className="px-4 pt-4 pb-3 flex items-center justify-between">
          <div className="text-[15px] font-semibold text-fg">Notificaciones</div>
          {unreadCount > 0 && (
            <button
              type="button"
              onClick={() => {
                markAllRead();
                toast.info("Notificaciones marcadas como leídas");
              }}
              className="text-[12px] font-medium text-primary hover:text-primary-hover cursor-pointer"
            >
              Marcar todas
            </button>
          )}
        </div>
        <div className="px-4 flex gap-1.5">
          <TabPill
            active={tab === "unread"}
            onClick={() => setTab("unread")}
            label="Sin leer"
            count={unreadCount}
          />
          <TabPill
            active={tab === "all"}
            onClick={() => setTab("all")}
            label="Todas"
            count={items.length}
          />
        </div>
        <div className="mt-2 max-h-[420px] overflow-y-auto">
          {visible.length === 0 ? (
            <div className="px-4 py-10 text-center text-[13px] text-muted">
              {tab === "unread"
                ? "Estás al día. No hay notificaciones sin leer."
                : "Sin notificaciones."}
            </div>
          ) : (
            visible.map((n) => (
              <NotificationItem
                key={n.id}
                notif={n}
                onClick={() => markRead(n.id)}
              />
            ))
          )}
        </div>
        <div className="border-t border-line px-4 py-3">
          <Link
            href="/reports"
            className="text-[13px] font-medium text-fg-2 hover:text-fg flex items-center justify-between"
          >
            Ver todas las actividades
            <span className="text-muted">→</span>
          </Link>
        </div>
      </Dropdown.Content>
    </Dropdown>
  );
}

function TabPill({
  active,
  onClick,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1.5 cursor-pointer transition-colors",
        active ? "bg-ink text-white" : "bg-surface-2 text-muted hover:text-fg-2"
      )}
    >
      {label}
      <span
        className={cn(
          "font-mono text-[10px] px-1.5 py-px rounded-full font-semibold",
          active ? "bg-white/20 text-white" : "bg-black/5 text-muted-2"
        )}
      >
        {count}
      </span>
    </button>
  );
}

