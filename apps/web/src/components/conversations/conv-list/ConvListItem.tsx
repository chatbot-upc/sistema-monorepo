import Link from "next/link";
import { cn } from "@/lib/cn";
import { Avatar } from "@/components/ui/Avatar";
import type { Conversation } from "@/lib/mock";
import type { ConvListFilter } from "./useConvListFilter";

interface ConvListItemProps {
  conv: Conversation;
  active: boolean;
  filter: ConvListFilter;
}

export function ConvListItem({ conv, active, filter }: ConvListItemProps) {
  const isEsc = conv.status === "escalated";
  const href =
    filter === "all"
      ? `/conversations/${conv.id}`
      : `/conversations/${conv.id}?filter=${filter}`;

  return (
    <Link
      href={href}
      className={cn(
        "grid grid-cols-[auto_1fr_auto] gap-3 p-3 rounded-xl cursor-pointer relative items-center transition-colors",
        isEsc
          ? "bg-primary-soft hover:bg-primary-soft/80"
          : active
            ? "bg-surface-2"
            : "hover:bg-surface-2"
      )}
    >
      {active && !isEsc && (
        <span className="absolute left-0 top-3 bottom-3 w-[3px] bg-primary rounded-sm" />
      )}
      <Avatar initials={conv.initials} gradient={conv.gradient} size="md" />
      <div className="min-w-0">
        <div className="text-[13px] font-semibold truncate">{conv.name}</div>
        <div className="text-xs text-muted truncate mt-0.5">{conv.preview}</div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <span className="font-mono text-[10px] text-muted">{conv.time}</span>
        {conv.unread && (
          <span className="w-[18px] h-[18px] bg-primary text-white rounded-full font-mono text-[10px] font-semibold flex items-center justify-center">
            {conv.unread}
          </span>
        )}
      </div>
    </Link>
  );
}
