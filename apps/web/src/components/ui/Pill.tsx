import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

type Tone =
  | "active"
  | "escalated"
  | "pending"
  | "closed"
  | "info"
  | "violet"
  | "amber"
  | "mint";

interface PillProps {
  tone?: Tone;
  dot?: boolean;
  children: ReactNode;
  className?: string;
  mono?: boolean;
}

const tones: Record<Tone, { bg: string; text: string; dot: string }> = {
  active: {
    bg: "bg-mint-soft",
    text: "text-success",
    dot: "bg-success",
  },
  escalated: {
    bg: "bg-primary-soft",
    text: "text-primary",
    dot: "bg-primary",
  },
  pending: {
    bg: "bg-amber-soft",
    text: "text-amber-fg",
    dot: "bg-amber",
  },
  closed: {
    bg: "bg-surface-2",
    text: "text-muted",
    dot: "bg-muted-2",
  },
  info: {
    bg: "bg-blue-soft",
    text: "text-blue",
    dot: "bg-blue",
  },
  violet: {
    bg: "bg-violet-soft",
    text: "text-violet",
    dot: "bg-violet",
  },
  amber: {
    bg: "bg-amber-soft",
    text: "text-amber-fg",
    dot: "bg-amber",
  },
  mint: {
    bg: "bg-mint-soft",
    text: "text-success",
    dot: "bg-success",
  },
};

export function Pill({
  tone = "active",
  dot = true,
  children,
  className,
  mono = false,
}: PillProps) {
  const t = tones[tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-[5px] rounded-full text-xs font-semibold",
        t.bg,
        t.text,
        mono && "font-mono",
        className
      )}
    >
      {dot && <span className={cn("w-1.5 h-1.5 rounded-full", t.dot)} />}
      {children}
    </span>
  );
}
