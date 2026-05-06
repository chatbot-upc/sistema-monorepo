"use client";

import {
  ChevronDown,
  ChevronRight,
  MoreHorizontal,
  Pencil,
  Trash2,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Pill } from "@/components/ui/Pill";
import { Dropdown } from "@/components/ui/Dropdown";
import { IconButton } from "@/components/ui/IconButton";
import type { Intent } from "@/lib/mock";

interface IntentRowProps {
  intent: Intent;
  open: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export function IntentRow({
  intent,
  open,
  onToggle,
  onEdit,
  onDelete,
}: IntentRowProps) {
  return (
    <Card variant="flush" className="overflow-hidden">
      <div className="flex items-center pr-4">
        <button
          type="button"
          onClick={onToggle}
          className="flex-1 flex items-center gap-4 px-6 py-5 cursor-pointer hover:bg-surface-2 transition-colors text-left"
          aria-expanded={open}
        >
          {open ? (
            <ChevronDown size={18} className="text-muted" strokeWidth={2} />
          ) : (
            <ChevronRight size={18} className="text-muted" strokeWidth={2} />
          )}
          <div className="flex-1 min-w-0">
            <div className="text-lg font-semibold tracking-[-0.2px] font-mono truncate">
              {intent.name}
            </div>
            <div className="font-mono text-[11px] text-muted mt-1">
              {intent.examples} ejemplos · umbral{" "}
              {intent.threshold.toFixed(2)}
            </div>
          </div>
          <Pill tone={intent.active ? "active" : "closed"}>
            {intent.active ? "Activa" : "Inactiva"}
          </Pill>
        </button>
        <IconButton
          variant="ghost"
          size="sm"
          onClick={onEdit}
          aria-label={`Editar ${intent.name}`}
        >
          <Pencil size={16} strokeWidth={2} />
        </IconButton>
        <Dropdown align="end">
          <Dropdown.Trigger>
            <IconButton
              variant="ghost"
              size="sm"
              aria-label={`Más acciones para ${intent.name}`}
            >
              <MoreHorizontal size={16} strokeWidth={2} />
            </IconButton>
          </Dropdown.Trigger>
          <Dropdown.Content>
            <Dropdown.Item
              icon={<Pencil size={14} strokeWidth={2} />}
              onSelect={onEdit}
            >
              Editar
            </Dropdown.Item>
            <Dropdown.Separator />
            <Dropdown.Item
              destructive
              icon={<Trash2 size={14} strokeWidth={2} />}
              onSelect={onDelete}
            >
              Eliminar
            </Dropdown.Item>
          </Dropdown.Content>
        </Dropdown>
      </div>

      {open ? (
        <div className="border-t border-line px-6 py-5 bg-surface-2">
          <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted mb-3">
            Ejemplos · {intent.samples.length} mostrados
          </div>
          <div className="flex flex-wrap gap-2">
            {intent.samples.map((sample, i) => (
              <div
                key={i}
                className="bg-surface px-4 py-2.5 rounded-full text-[13px] text-fg-2"
              >
                &ldquo;{sample}&rdquo;
              </div>
            ))}
            {intent.examples > intent.samples.length ? (
              <div className="px-4 py-2.5 rounded-full text-[13px] text-muted bg-surface border border-dashed border-line-2">
                + {intent.examples - intent.samples.length} más
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </Card>
  );
}
