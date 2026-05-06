import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "surface" | "dark" | "primary" | "primary-soft" | "ghost";
type Size = "sm" | "md" | "lg";

interface LinkIconButtonProps {
  href: string;
  variant?: Variant;
  size?: Size;
  children: ReactNode;
  className?: string;
  "aria-label"?: string;
}

const variants: Record<Variant, string> = {
  surface: "bg-surface text-fg-2 hover:text-primary",
  dark: "bg-ink text-white hover:bg-ink-soft",
  primary: "bg-primary text-white hover:bg-primary-hover",
  "primary-soft": "bg-primary-soft text-primary hover:bg-primary/10",
  ghost: "bg-surface-2 text-fg-2 hover:bg-line",
};

const sizes: Record<Size, string> = {
  sm: "w-9 h-9",
  md: "w-11 h-11",
  lg: "w-12 h-12",
};

export function LinkIconButton({
  href,
  variant = "surface",
  size = "md",
  children,
  className,
  "aria-label": ariaLabel,
}: LinkIconButtonProps) {
  return (
    <Link
      href={href}
      aria-label={ariaLabel}
      className={cn(
        "rounded-full flex items-center justify-center transition-colors flex-shrink-0",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </Link>
  );
}
