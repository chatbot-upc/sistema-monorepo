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
import { lockBodyScroll } from "@/lib/scroll-lock";
import { IconButton } from "./IconButton";

interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  width?: number;
  closeOnBackdrop?: boolean;
}

interface DrawerCtxShape {
  titleId: string;
  onClose: () => void;
}

const DrawerCtx = createContext<DrawerCtxShape | null>(null);
const useDrawerCtx = () => {
  const ctx = useContext(DrawerCtx);
  if (!ctx) throw new Error("Drawer subcomponents must be used inside <Drawer>");
  return ctx;
};

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function DrawerRoot({
  open,
  onOpenChange,
  children,
  width = 480,
  closeOnBackdrop = true,
}: DrawerProps) {
  const titleId = useId();
  const [mounted, setMounted] = useState(open);
  const [animState, setAnimState] = useState<"open" | "closed">(
    open ? "open" : "closed"
  );
  const panelRef = useRef<HTMLDivElement>(null);
  const previousActive = useRef<HTMLElement | null>(null);
  const onOpenChangeRef = useRef(onOpenChange);
  useEffect(() => {
    onOpenChangeRef.current = onOpenChange;
  }, [onOpenChange]);

  useEffect(() => {
    if (open) {
      previousActive.current = document.activeElement as HTMLElement | null;
      // Montaje-para-animacion: necesita el effect por el ciclo SSR/portal.
      // Vercel sugiere <Activity> a futuro. Ref: rendering-activity.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMounted(true);
      requestAnimationFrame(() => setAnimState("open"));
    } else if (mounted) {
      setAnimState("closed");
      const t = setTimeout(() => {
        setMounted(false);
        previousActive.current?.focus?.();
      }, 200);
      return () => clearTimeout(t);
    }
  }, [open, mounted]);

  useLayoutEffect(() => {
    if (!mounted) return;
    return lockBodyScroll();
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const panel = panelRef.current;
    if (!panel) return;
    panel.focus({ preventScroll: true });
  }, [mounted]);

  useEffect(() => {
    if (!mounted) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onOpenChangeRef.current(false);
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const nodes = Array.from(
          panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)
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
    <DrawerCtx.Provider
      value={{ titleId, onClose: () => onOpenChange(false) }}
    >
      <div
        className="fixed inset-0 z-overlay bg-ink/40 backdrop-blur-sm"
        data-anim="fade"
        data-state={animState}
        onMouseDown={(e) => {
          if (closeOnBackdrop && e.target === e.currentTarget) {
            onOpenChange(false);
          }
        }}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        data-anim="slide-right"
        data-state={animState}
        style={{ width }}
        className="fixed top-0 right-0 h-screen z-drawer bg-surface rounded-l-3xl shadow-modal flex flex-col outline-none"
      >
        {children}
      </div>
    </DrawerCtx.Provider>,
    document.body
  );
}

function DrawerHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  const { titleId, onClose } = useDrawerCtx();
  return (
    <div className="flex items-start justify-between gap-3 px-6 py-5 border-b border-line">
      <div className="min-w-0">
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
      >
        <X size={16} strokeWidth={2} />
      </IconButton>
    </div>
  );
}

function DrawerBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex-1 overflow-y-auto px-6 py-5", className)}>
      {children}
    </div>
  );
}

function DrawerFooter({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "px-6 py-5 border-t border-line flex justify-end gap-2",
        className
      )}
    >
      {children}
    </div>
  );
}

export const Drawer = Object.assign(DrawerRoot, {
  Header: DrawerHeader,
  Body: DrawerBody,
  Footer: DrawerFooter,
});
