import { cn } from "@/lib/cn";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export function Input({ className, error, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "h-11 px-[18px] bg-surface-2 rounded-full text-sm text-fg",
        "placeholder:text-muted-2 transition-shadow",
        "focus:shadow-[0_0_0_2px_var(--color-primary)]",
        error && "shadow-[0_0_0_2px_var(--color-primary)]",
        className
      )}
      {...props}
    />
  );
}
