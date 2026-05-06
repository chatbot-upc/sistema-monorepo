"use client";

import Link from "next/link";
import {
  AlertCircle,
  FileText,
  CheckCircle2,
  MessageSquare,
} from "lucide-react";
import { cn } from "@/lib/cn";
import type { Notif, NotifKind } from "./useNotifications";

const KIND_ICON: Record<
  NotifKind,
  {
    icon: React.ComponentType<{ size?: number; strokeWidth?: number }>;
    bg: string;
    color: string;
  }
> = {
  escalation: { icon: AlertCircle, bg: "bg-primary-soft", color: "text-primary" },
  doc: { icon: FileText, bg: "bg-blue-soft", color: "text-blue" },
  system: { icon: CheckCircle2, bg: "bg-success-soft", color: "text-success" },
  message: { icon: MessageSquare, bg: "bg-violet-soft", color: "text-violet" },
};

interface NotificationItemProps {
  notif: Notif;
  onClick: () => void;
}

export function NotificationItem({ notif, onClick }: NotificationItemProps) {
  const { icon: Icon, bg, color } = KIND_ICON[notif.kind];
  return (
    <Link
      href={notif.href}
      onClick={onClick}
      className={cn(
        "flex items-start gap-3 px-4 py-3 transition-colors hover:bg-bg-2",
        !notif.read && "bg-primary-soft/30 hover:bg-primary-soft/50"
      )}
    >
      <div
        className={cn(
          "shrink-0 w-9 h-9 rounded-full flex items-center justify-center",
          bg
        )}
      >
        <Icon size={16} strokeWidth={2} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span
            className={cn(
              "text-[13px] truncate",
              !notif.read ? "font-semibold text-fg" : "font-medium text-fg-2"
            )}
          >
            {notif.title}
          </span>
          <span className="font-mono text-[10px] text-muted shrink-0">
            {notif.time}
          </span>
        </div>
        <div className="text-xs text-fg-2 mt-0.5 line-clamp-2 leading-snug">
          {notif.description}
        </div>
      </div>
      {!notif.read && (
        <span
          className={cn("w-2 h-2 rounded-full bg-primary mt-2 shrink-0", color)}
        />
      )}
    </Link>
  );
}
