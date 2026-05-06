"use client";

import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/cn";

export type ToastVariant = "success" | "error" | "info";

export interface ToastData {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const variantStyles: Record<
  ToastVariant,
  { icon: React.ComponentType<{ size?: number; className?: string; strokeWidth?: number }>; color: string }
> = {
  success: { icon: CheckCircle2, color: "text-success" },
  error: { icon: AlertCircle, color: "text-primary" },
  info: { icon: Info, color: "text-blue" },
};

interface ToastItemProps {
  toast: ToastData;
  onDismiss: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
}

export function ToastItem({
  toast,
  onDismiss,
  onPause,
  onResume,
}: ToastItemProps) {
  const { icon: Icon, color } = variantStyles[toast.variant];
  return (
    <div
      role="status"
      aria-live="polite"
      data-anim="slide-up"
      data-state="open"
      onMouseEnter={() => onPause(toast.id)}
      onMouseLeave={() => onResume(toast.id)}
      className={cn(
        "bg-surface rounded-2xl shadow-overlay border border-line",
        "px-4 py-3 min-w-[320px] max-w-[420px]",
        "flex items-start gap-3 pointer-events-auto"
      )}
    >
      <Icon size={18} className={cn("shrink-0 mt-0.5", color)} strokeWidth={2} />
      <div className="flex-1 min-w-0">
        <div className="text-[13px] font-semibold text-fg leading-snug">
          {toast.title}
        </div>
        {toast.description && (
          <div className="text-xs text-fg-2 mt-0.5 leading-relaxed">
            {toast.description}
          </div>
        )}
      </div>
      {toast.action && (
        <button
          type="button"
          onClick={() => {
            toast.action?.onClick();
            onDismiss(toast.id);
          }}
          className="text-[13px] font-semibold text-primary hover:text-primary-hover shrink-0 cursor-pointer"
        >
          {toast.action.label}
        </button>
      )}
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Cerrar"
        className="shrink-0 text-muted hover:text-fg-2 cursor-pointer transition-colors"
      >
        <X size={14} strokeWidth={2} />
      </button>
    </div>
  );
}
