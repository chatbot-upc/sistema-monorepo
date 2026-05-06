"use client";

import {
  Children,
  cloneElement,
  createContext,
  isValidElement,
  useCallback,
  useContext,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";

type Align = "start" | "end";
type Side = "bottom" | "top";

interface DropdownProps {
  children: ReactNode;
  align?: Align;
  side?: Side;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

interface DropdownCtxShape {
  open: boolean;
  setOpen: (v: boolean) => void;
  triggerRef: React.RefObject<HTMLElement | null>;
  contentId: string;
  align: Align;
  side: Side;
}

const DropdownCtx = createContext<DropdownCtxShape | null>(null);

const useDropdownCtx = () => {
  const ctx = useContext(DropdownCtx);
  if (!ctx) throw new Error("Dropdown subcomponents must be used inside <Dropdown>");
  return ctx;
};

function DropdownRoot({
  children,
  align = "start",
  side = "bottom",
  open: openProp,
  onOpenChange,
}: DropdownProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = openProp ?? internalOpen;
  const setOpen = (v: boolean) => {
    if (openProp === undefined) setInternalOpen(v);
    onOpenChange?.(v);
  };
  const triggerRef = useRef<HTMLElement | null>(null);
  const contentId = useId();

  return (
    <DropdownCtx.Provider
      value={{ open, setOpen, triggerRef, contentId, align, side }}
    >
      {children}
    </DropdownCtx.Provider>
  );
}

interface TriggerProps {
  children: ReactElement<{
    ref?: React.Ref<HTMLElement>;
    onClick?: (e: React.MouseEvent) => void;
    "aria-haspopup"?: string;
    "aria-expanded"?: boolean;
    "aria-controls"?: string;
  }>;
  asChild?: boolean;
}

function DropdownTrigger({ children }: TriggerProps) {
  const { open, setOpen, triggerRef, contentId } = useDropdownCtx();
  const child = Children.only(children);
  if (!isValidElement(child)) return null;

  const childProps = child.props ?? {};
  const childOnClick = childProps.onClick;

  return cloneElement(child, {
    ref: (node: HTMLElement | null) => {
      triggerRef.current = node;
    },
    onClick: (e: React.MouseEvent) => {
      childOnClick?.(e);
      setOpen(!open);
    },
    "aria-haspopup": "menu",
    "aria-expanded": open,
    "aria-controls": contentId,
  });
}

interface ContentProps {
  children: ReactNode;
  className?: string;
  minWidth?: number;
  sideOffset?: number;
}

function DropdownContent({
  children,
  className,
  minWidth = 180,
  sideOffset = 6,
}: ContentProps) {
  const { open, setOpen, triggerRef, contentId, align, side } = useDropdownCtx();
  const contentRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (open) setMounted(true);
    else {
      const t = setTimeout(() => setMounted(false), 140);
      return () => clearTimeout(t);
    }
  }, [open]);

  const recompute = useCallback(() => {
    if (!triggerRef.current || !contentRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    const c = contentRef.current.getBoundingClientRect();
    let top = side === "bottom" ? r.bottom + sideOffset : r.top - c.height - sideOffset;
    let left = align === "start" ? r.left : r.right - c.width;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (left + c.width > vw - 8) left = vw - c.width - 8;
    if (left < 8) left = 8;
    if (top + c.height > vh - 8) top = r.top - c.height - sideOffset;
    if (top < 8) top = r.bottom + sideOffset;
    setPos({ top, left });
  }, [align, side, sideOffset, triggerRef]);

  useLayoutEffect(() => {
    if (!mounted) return;
    recompute();
  }, [mounted, recompute]);

  useEffect(() => {
    if (!open) return;
    const onWindow = () => recompute();
    window.addEventListener("scroll", onWindow, true);
    window.addEventListener("resize", onWindow);
    return () => {
      window.removeEventListener("scroll", onWindow, true);
      window.removeEventListener("resize", onWindow);
    };
  }, [open, recompute]);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        contentRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setOpen(false);
        (triggerRef.current as HTMLElement | null)?.focus?.();
      }
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, setOpen, triggerRef]);

  if (!mounted || typeof window === "undefined") return null;

  return createPortal(
    <div
      ref={contentRef}
      id={contentId}
      role="menu"
      data-anim="slide-up"
      data-state={open ? "open" : "closed"}
      style={{
        position: "fixed",
        top: pos?.top ?? -9999,
        left: pos?.left ?? -9999,
        minWidth,
        visibility: pos ? "visible" : "hidden",
      }}
      className={cn(
        "z-dropdown bg-surface rounded-2xl shadow-overlay border border-line p-1.5",
        className
      )}
    >
      {children}
    </div>,
    document.body
  );
}

interface ItemProps {
  children: ReactNode;
  onSelect?: () => void;
  destructive?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
  className?: string;
}

function DropdownItem({
  children,
  onSelect,
  destructive,
  disabled,
  icon,
  className,
}: ItemProps) {
  const { setOpen } = useDropdownCtx();
  return (
    <button
      type="button"
      role="menuitem"
      disabled={disabled}
      onClick={() => {
        if (disabled) return;
        onSelect?.();
        setOpen(false);
      }}
      className={cn(
        "w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium text-fg-2 cursor-pointer transition-colors text-left",
        "hover:bg-bg-2 hover:text-fg",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent",
        destructive && "text-primary hover:bg-primary-soft hover:text-primary",
        className
      )}
    >
      {icon && <span className="shrink-0 text-muted">{icon}</span>}
      <span className="flex-1 truncate">{children}</span>
    </button>
  );
}

function DropdownSeparator() {
  return <div role="separator" className="h-px bg-line my-1.5 mx-1" />;
}

function DropdownLabel({ children }: { children: ReactNode }) {
  return (
    <div className="px-3 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted">
      {children}
    </div>
  );
}

export const Dropdown = Object.assign(DropdownRoot, {
  Trigger: DropdownTrigger,
  Content: DropdownContent,
  Item: DropdownItem,
  Separator: DropdownSeparator,
  Label: DropdownLabel,
});
