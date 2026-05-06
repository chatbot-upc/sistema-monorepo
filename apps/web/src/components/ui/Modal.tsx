"use client";

import {
  createContext,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { IconButton } from "./IconButton";

type Size = "sm" | "md" | "lg" | "xl";

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  size?: Size;
  children: ReactNode;
  className?: string;
  closeOnBackdrop?: boolean;
}

interface ModalCtxShape {
  titleId: string;
  onClose: () => void;
}

const ModalCtx = createContext<ModalCtxShape | null>(null);

const useModalCtx = () => {
  const ctx = useContext(ModalCtx);
  if (!ctx) throw new Error("Modal subcomponents must be used inside <Modal>");
  return ctx;
};

const sizeMap: Record<Size, string> = {
  sm: "max-w-[400px]",
  md: "max-w-[480px]",
  lg: "max-w-[640px]",
  xl: "max-w-[800px]",
};

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function ModalRoot({
  open,
  onOpenChange,
  size = "md",
  children,
  className,
  closeOnBackdrop = true,
}: ModalProps) {
  const titleId = useId();
  const [mounted, setMounted] = useState(open);
  const [animState, setAnimState] = useState<"open" | "closed">(
    open ? "open" : "closed"
  );
  const cardRef = useRef<HTMLDivElement>(null);
  const previousActive = useRef<HTMLElement | null>(null);
  const onOpenChangeRef = useRef(onOpenChange);
  useEffect(() => {
    onOpenChangeRef.current = onOpenChange;
  }, [onOpenChange]);

  useEffect(() => {
    if (open) {
      previousActive.current = document.activeElement as HTMLElement | null;
      setMounted(true);
      requestAnimationFrame(() => setAnimState("open"));
    } else if (mounted) {
      setAnimState("closed");
      const t = setTimeout(() => {
        setMounted(false);
        previousActive.current?.focus?.();
      }, 160);
      return () => clearTimeout(t);
    }
  }, [open, mounted]);

  useLayoutEffect(() => {
    if (!mounted) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const card = cardRef.current;
    if (!card) return;
    card.focus({ preventScroll: true });
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onOpenChangeRef.current(false);
        return;
      }
      if (e.key === "Tab" && cardRef.current) {
        const nodes = Array.from(
          cardRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)
        );
        if (nodes.length === 0) {
          e.preventDefault();
          return;
        }
        const first = nodes[0];
        const last = nodes[nodes.length - 1];
        const active = document.activeElement as HTMLElement | null;
        if (e.shiftKey && active === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && active === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mounted]);

  if (!mounted || typeof window === "undefined") return null;

  return createPortal(
    <ModalCtx.Provider
      value={{ titleId, onClose: () => onOpenChange(false) }}
    >
      <div
        className="fixed inset-0 z-overlay flex items-center justify-center p-4 bg-ink/40 backdrop-blur-sm"
        data-anim="fade"
        data-state={animState}
        onMouseDown={(e) => {
          if (closeOnBackdrop && e.target === e.currentTarget) {
            onOpenChange(false);
          }
        }}
      >
        <div
          ref={cardRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          tabIndex={-1}
          data-anim="scale"
          data-state={animState}
          className={cn(
            "relative bg-surface rounded-3xl shadow-modal w-full p-6 outline-none focus:outline-none focus-visible:outline-none",
            sizeMap[size],
            className
          )}
        >
          {children}
        </div>
      </div>
    </ModalCtx.Provider>,
    document.body
  );
}

interface HeaderProps {
  title: string;
  description?: string;
  icon?: ReactNode;
}

function ModalHeader({ title, description, icon }: HeaderProps) {
  const { titleId, onClose } = useModalCtx();
  return (
    <div className="flex items-start gap-3 pr-10">
      {icon && <div className="shrink-0 mt-0.5">{icon}</div>}
      <div className="flex-1 min-w-0">
        <h2
          id={titleId}
          className="text-[18px] font-semibold tracking-[-0.2px] text-fg"
        >
          {title}
        </h2>
        {description && (
          <p className="text-[13px] text-fg-2 mt-1 leading-relaxed">
            {description}
          </p>
        )}
      </div>
      <IconButton
        variant="ghost"
        size="sm"
        onClick={onClose}
        aria-label="Cerrar"
        className="absolute top-4 right-4"
      >
        <X size={16} strokeWidth={2} />
      </IconButton>
    </div>
  );
}

function ModalBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col gap-4 pt-5", className)}>{children}</div>
  );
}

function ModalFooter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex justify-end gap-2 pt-5 mt-5 border-t border-line",
        className
      )}
    >
      {children}
    </div>
  );
}

export const Modal = Object.assign(ModalRoot, {
  Header: ModalHeader,
  Body: ModalBody,
  Footer: ModalFooter,
});
