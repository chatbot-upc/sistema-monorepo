import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "dark" | "ghost" | "destructive";
type Size = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children?: ReactNode;
}

const base =
  "inline-flex items-center gap-2 font-medium rounded-full cursor-pointer transition-all whitespace-nowrap disabled:opacity-40 disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "bg-primary text-white hover:bg-primary-hover",
  secondary: "bg-surface text-fg hover:bg-bg-2",
  dark: "bg-ink text-white hover:bg-ink-soft",
  ghost: "text-fg-2 hover:bg-bg-2",
  destructive:
    "bg-transparent text-primary border border-primary hover:bg-primary-soft",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-4 text-[13px]",
  md: "h-11 px-5 text-[13px]",
  lg: "h-12 px-6 text-[14px]",
  icon: "w-11 h-11 p-0 justify-center",
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(base, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  );
}
