"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { ToastItem, type ToastData, type ToastVariant } from "./Toast";

const MAX_VISIBLE = 4;
const DEFAULT_DURATION: Record<ToastVariant, number> = {
  success: 4000,
  info: 4000,
  error: 6000,
};

interface ToastOptions {
  description?: string;
  action?: { label: string; onClick: () => void };
  duration?: number;
}

interface ToastApi {
  success: (title: string, opts?: ToastOptions) => string;
  error: (title: string, opts?: ToastOptions) => string;
  info: (title: string, opts?: ToastOptions) => string;
  dismiss: (id: string) => void;
}

interface ToastContextShape {
  toast: ToastApi;
}

const ToastContext = createContext<ToastContextShape | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const [mounted, setMounted] = useState(false);
  const timers = useRef(new Map<string, { remaining: number; startedAt: number; timeout: ReturnType<typeof setTimeout> | null }>());

  useEffect(() => setMounted(true), []);

  const dismiss = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (t?.timeout) clearTimeout(t.timeout);
    timers.current.delete(id);
    setToasts((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const scheduleDismiss = useCallback(
    (id: string, ms: number) => {
      const startedAt = Date.now();
      const timeout = setTimeout(() => dismiss(id), ms);
      timers.current.set(id, { remaining: ms, startedAt, timeout });
    },
    [dismiss]
  );

  const pause = useCallback((id: string) => {
    const t = timers.current.get(id);
    if (!t || !t.timeout) return;
    clearTimeout(t.timeout);
    const elapsed = Date.now() - t.startedAt;
    timers.current.set(id, {
      remaining: Math.max(0, t.remaining - elapsed),
      startedAt: Date.now(),
      timeout: null,
    });
  }, []);

  const resume = useCallback(
    (id: string) => {
      const t = timers.current.get(id);
      if (!t || t.timeout) return;
      const timeout = setTimeout(() => dismiss(id), t.remaining);
      timers.current.set(id, { ...t, startedAt: Date.now(), timeout });
    },
    [dismiss]
  );

  const push = useCallback(
    (variant: ToastVariant, title: string, opts: ToastOptions = {}) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const next: ToastData = {
        id,
        variant,
        title,
        description: opts.description,
        action: opts.action,
      };
      setToasts((prev) => {
        const updated = [...prev, next];
        if (updated.length > MAX_VISIBLE) {
          const overflow = updated.slice(0, updated.length - MAX_VISIBLE);
          overflow.forEach((t) => {
            const tm = timers.current.get(t.id);
            if (tm?.timeout) clearTimeout(tm.timeout);
            timers.current.delete(t.id);
          });
          return updated.slice(-MAX_VISIBLE);
        }
        return updated;
      });
      scheduleDismiss(id, opts.duration ?? DEFAULT_DURATION[variant]);
      return id;
    },
    [scheduleDismiss]
  );

  const value = useMemo<ToastContextShape>(
    () => ({
      toast: {
        success: (title, opts) => push("success", title, opts),
        error: (title, opts) => push("error", title, opts),
        info: (title, opts) => push("info", title, opts),
        dismiss,
      },
    }),
    [push, dismiss]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {mounted &&
        createPortal(
          <div
            aria-live="polite"
            className="fixed bottom-6 right-6 z-toast flex flex-col-reverse gap-2 pointer-events-none"
          >
            {toasts.map((t) => (
              <ToastItem
                key={t.id}
                toast={t}
                onDismiss={dismiss}
                onPause={pause}
                onResume={resume}
              />
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}
