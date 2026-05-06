import { cn } from "@/lib/cn";
import type { HTMLAttributes } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "compact" | "flush";
}

export function Card({
  variant = "default",
  className,
  children,
  ...props
}: CardProps) {
  const padding = {
    default: "p-6",
    compact: "p-5",
    flush: "p-0 overflow-hidden",
  }[variant];

  return (
    <div
      className={cn("bg-surface rounded-3xl", padding, className)}
      {...props}
    >
      {children}
    </div>
  );
}
