"use client";

import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  showCounter?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  function Textarea(
    { className, showCounter, value, maxLength, ...props },
    ref
  ) {
    const length =
      typeof value === "string"
        ? value.length
        : Array.isArray(value)
          ? value.join("").length
          : 0;
    return (
      <div className="flex flex-col gap-1">
        <textarea
          ref={ref}
          value={value}
          maxLength={maxLength}
          className={cn(
            "bg-surface-2 rounded-2xl px-4 py-3 text-[13px] resize-none transition-shadow outline-none w-full",
            "focus:bg-surface focus:shadow-[0_0_0_2px_var(--color-primary)]",
            "placeholder:text-muted-2",
            className
          )}
          {...props}
        />
        {showCounter && maxLength && (
          <div className="text-[10px] font-mono text-muted text-right pr-2">
            {length}/{maxLength}
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";
