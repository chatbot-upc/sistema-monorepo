"use client";

import { useState } from "react";
import { ChevronDown, Check } from "lucide-react";
import { Dropdown } from "./Dropdown";
import { cn } from "@/lib/cn";

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
  description?: string;
}

interface SingleProps<T extends string> {
  multi?: false;
  value: T;
  onChange: (v: T) => void;
}

interface MultiProps<T extends string> {
  multi: true;
  value: T[];
  onChange: (v: T[]) => void;
}

type SelectProps<T extends string> = {
  options: SelectOption<T>[];
  placeholder?: string;
  label?: string;
  className?: string;
  align?: "start" | "end";
} & (SingleProps<T> | MultiProps<T>);

export function Select<T extends string>(props: SelectProps<T>) {
  const {
    options,
    placeholder = "Seleccionar",
    label,
    className,
    align = "start",
  } = props;

  let triggerLabel: string;
  let isActive: boolean;

  if (props.multi) {
    const count = props.value.length;
    if (count === 0) {
      triggerLabel = label ? `${label} · todos` : placeholder;
      isActive = false;
    } else if (count === 1) {
      const opt = options.find((o) => o.value === props.value[0]);
      triggerLabel = label ? `${label} · ${opt?.label ?? ""}` : (opt?.label ?? "");
      isActive = true;
    } else {
      triggerLabel = label
        ? `${label} · ${count} seleccionados`
        : `${count} seleccionados`;
      isActive = true;
    }
  } else {
    const opt = options.find((o) => o.value === props.value);
    triggerLabel = opt
      ? label
        ? `${label} · ${opt.label}`
        : opt.label
      : placeholder;
    isActive = !!opt;
  }

  const isSelected = (v: T): boolean =>
    props.multi ? props.value.includes(v) : props.value === v;

  const [open, setOpen] = useState(false);

  const handleSelect = (v: T) => {
    if (props.multi) {
      const set = new Set(props.value);
      if (set.has(v)) set.delete(v);
      else set.add(v);
      props.onChange(Array.from(set) as T[]);
    } else {
      props.onChange(v);
      setOpen(false);
    }
  };

  return (
    <Dropdown align={align} open={open} onOpenChange={setOpen}>
      <Dropdown.Trigger>
        <button
          type="button"
          className={cn(
            "h-11 px-4 rounded-full text-[13px] font-medium inline-flex items-center gap-2 cursor-pointer transition-colors whitespace-nowrap",
            isActive
              ? "bg-ink text-white hover:bg-ink-soft"
              : "bg-surface text-fg hover:bg-bg-2",
            className
          )}
        >
          <span className="truncate">{triggerLabel}</span>
          <ChevronDown size={14} strokeWidth={2} className="shrink-0 opacity-70" />
        </button>
      </Dropdown.Trigger>
      <Dropdown.Content minWidth={220}>
        {options.map((o) => {
          const selected = isSelected(o.value);
          return (
            <button
              key={o.value}
              type="button"
              onClick={() => {
                handleSelect(o.value);
              }}
              className={cn(
                "w-full flex items-start gap-2.5 px-3 py-2 rounded-xl text-[13px] cursor-pointer text-left transition-colors",
                "hover:bg-bg-2",
                selected && "bg-primary-soft/50"
              )}
            >
              <span
                className={cn(
                  "w-4 h-4 rounded-md flex items-center justify-center border shrink-0 mt-0.5",
                  props.multi
                    ? selected
                      ? "bg-primary border-primary"
                      : "border-line-2 bg-surface"
                    : selected
                      ? "bg-primary border-primary"
                      : "border-transparent"
                )}
              >
                {selected && <Check size={11} className="text-white" strokeWidth={2.5} />}
              </span>
              <span className="flex-1 min-w-0">
                <span
                  className={cn(
                    "font-medium block",
                    selected ? "text-fg" : "text-fg-2"
                  )}
                >
                  {o.label}
                </span>
                {o.description && (
                  <span className="text-[11px] text-muted block mt-0.5">
                    {o.description}
                  </span>
                )}
              </span>
            </button>
          );
        })}
      </Dropdown.Content>
    </Dropdown>
  );
}
