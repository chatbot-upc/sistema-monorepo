"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/cn";
import {
  MONTHS_FULL,
  WEEKDAYS_ES,
  addDays,
  formatPill,
  isSameDay,
  startOfDay,
} from "@/lib/dates";
import { Button } from "./Button";

export interface DateRange {
  start: Date;
  end: Date;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
  className?: string;
}

interface Preset {
  key: string;
  label: string;
  build: () => DateRange;
}

const PRESETS: Preset[] = [
  {
    key: "7d",
    label: "Últimos 7 días",
    build: () => {
      const end = startOfDay(new Date());
      return { start: addDays(end, -6), end };
    },
  },
  {
    key: "30d",
    label: "Últimos 30 días",
    build: () => {
      const end = startOfDay(new Date());
      return { start: addDays(end, -29), end };
    },
  },
  {
    key: "thisMonth",
    label: "Este mes",
    build: () => {
      const today = startOfDay(new Date());
      const start = new Date(today.getFullYear(), today.getMonth(), 1);
      return { start, end: today };
    },
  },
  {
    key: "lastMonth",
    label: "Mes pasado",
    build: () => {
      const today = startOfDay(new Date());
      const start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const end = new Date(today.getFullYear(), today.getMonth(), 0);
      return { start, end };
    },
  },
];

export function DateRangePicker({
  value,
  onChange,
  className,
}: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={cn(
          "flex items-center gap-3 bg-surface-2 hover:bg-bg-2 transition-colors rounded-full px-5 py-3 cursor-pointer",
          className
        )}
      >
        <Calendar size={16} className="text-fg-2" strokeWidth={2} />
        <span className="font-mono text-[13px] font-medium">
          {formatPill(value.start)}
        </span>
        <span className="text-muted">→</span>
        <span className="font-mono text-[13px] font-medium">
          {formatPill(value.end)}
        </span>
      </button>
      {open ? (
        <RangePopover
          value={value}
          triggerRef={triggerRef}
          onApply={(r) => {
            onChange(r);
            setOpen(false);
          }}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}

interface RangePopoverProps {
  value: DateRange;
  triggerRef: React.RefObject<HTMLButtonElement | null>;
  onApply: (r: DateRange) => void;
  onClose: () => void;
}

function RangePopover({
  value,
  triggerRef,
  onApply,
  onClose,
}: RangePopoverProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const [draftStart, setDraftStart] = useState<Date>(value.start);
  const [draftEnd, setDraftEnd] = useState<Date | null>(value.end);
  const [hover, setHover] = useState<Date | null>(null);
  const [viewMonth, setViewMonth] = useState<Date>(
    new Date(value.start.getFullYear(), value.start.getMonth(), 1)
  );

  // Posicionamiento — patrón espejo de Dropdown.tsx:133-162
  const recompute = useCallback(() => {
    if (!triggerRef.current || !panelRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    const p = panelRef.current.getBoundingClientRect();
    let top = r.bottom + 8;
    let left = r.left;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (left + p.width > vw - 8) left = vw - p.width - 8;
    if (left < 8) left = 8;
    if (top + p.height > vh - 8) top = r.top - p.height - 8;
    setPos({ top, left });
  }, [triggerRef]);

  useLayoutEffect(() => {
    recompute();
  }, [recompute]);

  useEffect(() => {
    const onWindow = () => recompute();
    window.addEventListener("scroll", onWindow, true);
    window.addEventListener("resize", onWindow);
    return () => {
      window.removeEventListener("scroll", onWindow, true);
      window.removeEventListener("resize", onWindow);
    };
  }, [recompute]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const onClick = (e: MouseEvent) => {
      const t = e.target as Node;
      if (
        panelRef.current?.contains(t) ||
        triggerRef.current?.contains(t)
      ) {
        return;
      }
      onClose();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [onClose, triggerRef]);

  // State machine clara: si end===null estamos a mitad de selección,
  // el próximo click completa el rango (con swap si va hacia atrás).
  // Si el rango está completo, click empieza una nueva selección.
  const handleDayClick = (day: Date) => {
    if (draftEnd === null) {
      if (day < draftStart) {
        setDraftEnd(draftStart);
        setDraftStart(day);
      } else {
        setDraftEnd(day);
      }
      return;
    }
    setDraftStart(day);
    setDraftEnd(null);
  };

  const applyPreset = (p: Preset) => {
    const r = p.build();
    setDraftStart(r.start);
    setDraftEnd(r.end);
    setViewMonth(new Date(r.start.getFullYear(), r.start.getMonth(), 1));
  };

  if (typeof window === "undefined") return null;

  return createPortal(
    <div
      ref={panelRef}
      role="dialog"
      aria-label="Seleccionar rango de fechas"
      className="fixed z-dropdown bg-surface rounded-2xl shadow-modal border border-line p-4 flex gap-4"
      style={{
        top: pos?.top ?? -9999,
        left: pos?.left ?? -9999,
        visibility: pos ? "visible" : "hidden",
        width: 540,
      }}
    >
      {/* Presets */}
      <div className="flex flex-col gap-1 w-[140px] border-r border-line pr-3">
        <div className="text-[10px] uppercase tracking-wide font-semibold text-muted px-2 mb-1">
          Atajos
        </div>
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => applyPreset(p)}
            className="text-left px-3 py-2 rounded-lg text-[13px] hover:bg-surface-2 transition-colors cursor-pointer text-fg-2"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Calendar */}
      <div className="flex-1 flex flex-col gap-3">
        <CalendarHeader
          viewMonth={viewMonth}
          onPrev={() =>
            setViewMonth(
              new Date(viewMonth.getFullYear(), viewMonth.getMonth() - 1, 1)
            )
          }
          onNext={() =>
            setViewMonth(
              new Date(viewMonth.getFullYear(), viewMonth.getMonth() + 1, 1)
            )
          }
        />
        <CalendarGrid
          viewMonth={viewMonth}
          start={draftStart}
          end={draftEnd}
          hover={hover}
          onHover={setHover}
          onClick={handleDayClick}
        />
        <div className="flex justify-between items-center pt-3 border-t border-line">
          <span className="font-mono text-[12px] text-muted">
            {formatPill(draftStart)}
            {draftEnd !== null && !isSameDay(draftStart, draftEnd)
              ? ` → ${formatPill(draftEnd)}`
              : ""}
          </span>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={onClose}>
              Cancelar
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() =>
                onApply({
                  start: draftStart,
                  end: draftEnd ?? draftStart,
                })
              }
            >
              Aplicar
            </Button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

interface CalendarHeaderProps {
  viewMonth: Date;
  onPrev: () => void;
  onNext: () => void;
}

function CalendarHeader({ viewMonth, onPrev, onNext }: CalendarHeaderProps) {
  return (
    <div className="flex items-center justify-between px-1">
      <button
        type="button"
        onClick={onPrev}
        className="w-7 h-7 rounded-lg hover:bg-surface-2 flex items-center justify-center cursor-pointer"
        aria-label="Mes anterior"
      >
        <ChevronLeft size={16} strokeWidth={2} className="text-fg-2" />
      </button>
      <span className="text-[13px] font-semibold tracking-[-0.1px]">
        {MONTHS_FULL[viewMonth.getMonth()]} {viewMonth.getFullYear()}
      </span>
      <button
        type="button"
        onClick={onNext}
        className="w-7 h-7 rounded-lg hover:bg-surface-2 flex items-center justify-center cursor-pointer"
        aria-label="Mes siguiente"
      >
        <ChevronRight size={16} strokeWidth={2} className="text-fg-2" />
      </button>
    </div>
  );
}

interface CalendarGridProps {
  viewMonth: Date;
  start: Date;
  end: Date | null;
  hover: Date | null;
  onHover: (d: Date | null) => void;
  onClick: (d: Date) => void;
}

function CalendarGrid({
  viewMonth,
  start,
  end,
  hover,
  onHover,
  onClick,
}: CalendarGridProps) {
  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  // ISO weekday: lunes=0
  const firstWeekday = (firstDay.getDay() + 6) % 7;
  const cells: (Date | null)[] = [];
  for (let i = 0; i < firstWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(new Date(year, month, d));
  while (cells.length % 7 !== 0) cells.push(null);

  // Hover preview bidireccional: cuando end es null, el hover define
  // dinámicamente el otro extremo del rango (puede estar antes o después
  // del start ya seleccionado).
  let rangeStart: Date;
  let rangeEnd: Date;
  if (end !== null) {
    rangeStart = start;
    rangeEnd = end;
  } else if (hover !== null) {
    if (hover < start) {
      rangeStart = hover;
      rangeEnd = start;
    } else {
      rangeStart = start;
      rangeEnd = hover;
    }
  } else {
    rangeStart = start;
    rangeEnd = start;
  }

  const today = startOfDay(new Date());

  return (
    <div
      className="grid grid-cols-7 gap-y-2"
      onMouseLeave={() => onHover(null)}
    >
      {WEEKDAYS_ES.map((w, i) => (
        <span
          key={i}
          className="text-[11px] font-mono text-muted text-center py-1"
        >
          {w}
        </span>
      ))}
      {cells.map((cell, i) => {
        if (!cell) return <span key={i} className="h-9" />;
        const colInWeek = i % 7;
        const isWeekStart = colInWeek === 0;
        const isWeekEnd = colInWeek === 6;
        const inRange = cell >= rangeStart && cell <= rangeEnd;
        const isStart = isSameDay(cell, rangeStart);
        const isEnd = isSameDay(cell, rangeEnd);
        const isSingle = isStart && isEnd;
        const roundLeft = isStart || (inRange && isWeekStart);
        const roundRight = isEnd || (inRange && isWeekEnd);
        const isToday = isSameDay(cell, today);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onClick(cell)}
            onMouseEnter={() => onHover(cell)}
            className={cn(
              "h-9 text-[12.5px] font-mono cursor-pointer transition-colors",
              inRange && !isStart && !isEnd && "bg-primary-soft text-primary",
              (isStart || isEnd) && "bg-primary text-white font-semibold",
              !inRange && !isStart && !isEnd && "hover:bg-surface-2 text-fg-2 rounded-lg",
              isSingle && "rounded-lg",
              !isSingle && roundLeft && "rounded-l-lg",
              !isSingle && roundRight && "rounded-r-lg",
              isToday && !inRange && !isStart && !isEnd && "ring-1 ring-line-2"
            )}
          >
            {cell.getDate()}
          </button>
        );
      })}
    </div>
  );
}
