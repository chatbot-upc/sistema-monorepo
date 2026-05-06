"use client";

import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import {
  useReportForm,
  type RangePreset,
  type ReportFormat,
} from "./useReportForm";

const RANGES: { value: RangePreset; label: string }[] = [
  { value: "7d", label: "Últimos 7 días" },
  { value: "30d", label: "Últimos 30 días" },
  { value: "thisMonth", label: "Este mes" },
  { value: "lastMonth", label: "Mes pasado" },
];

const FORMATS: { value: ReportFormat; label: string; description: string }[] = [
  { value: "pdf", label: "PDF", description: "Reporte ejecutivo" },
  { value: "excel", label: "Excel", description: "Datos tabulares" },
  { value: "csv", label: "CSV", description: "Crudo, máx detalle" },
];

const SECTIONS = [
  { key: "intenciones", label: "Top intenciones" },
  { key: "conversaciones", label: "Conversaciones y escalaciones" },
  { key: "satisfaccion", label: "Satisfacción y NPS" },
  { key: "costos", label: "Costos y tokens" },
];

interface ReportModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function ReportModal({ open, onOpenChange }: ReportModalProps) {
  const form = useReportForm();
  const { toast } = useToast();

  const handleSubmit = async () => {
    if (form.sections.size === 0) {
      toast.error("Selecciona al menos una sección");
      return;
    }
    form.setSubmitting(true);
    await new Promise((r) => setTimeout(r, 600));
    form.setSubmitting(false);
    onOpenChange(false);
    toast.success("Reporte en cola", {
      description: `Formato ${form.format.toUpperCase()} · ${form.sections.size} secciones · te avisaremos al estar listo.`,
      action: {
        label: "Ver descargas",
        onClick: () => toast.info("Abriendo bandeja de descargas..."),
      },
    });
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="md">
      <Modal.Header
        title="Generar reporte"
        description="Selecciona el rango, formato y secciones a incluir."
      />
      <Modal.Body>
        <Field label="Rango">
          <PillGroup
            options={RANGES}
            value={form.range}
            onChange={form.setRange}
          />
        </Field>

        <Field label="Formato">
          <div className="grid grid-cols-3 gap-2">
            {FORMATS.map((f) => {
              const active = form.format === f.value;
              return (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => form.setFormat(f.value)}
                  className={cn(
                    "rounded-2xl px-4 py-3 text-left border transition-colors cursor-pointer",
                    active
                      ? "bg-ink text-white border-ink"
                      : "bg-surface-2 border-transparent hover:bg-bg-2 text-fg"
                  )}
                >
                  <div className="text-[13px] font-semibold">{f.label}</div>
                  <div
                    className={cn(
                      "text-[11px] mt-0.5",
                      active ? "text-white/70" : "text-muted"
                    )}
                  >
                    {f.description}
                  </div>
                </button>
              );
            })}
          </div>
        </Field>

        <Field label="Secciones">
          <div className="flex flex-col gap-1.5">
            {SECTIONS.map((s) => {
              const checked = form.sections.has(s.key);
              return (
                <label
                  key={s.key}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-xl cursor-pointer transition-colors text-[13px]",
                    checked ? "bg-primary-soft" : "hover:bg-bg-2"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => form.toggleSection(s.key)}
                    className="sr-only"
                  />
                  <span
                    className={cn(
                      "w-4 h-4 rounded-md flex items-center justify-center border transition-colors shrink-0",
                      checked
                        ? "bg-primary border-primary"
                        : "border-line-2 bg-surface"
                    )}
                  >
                    {checked && (
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 10 10"
                        fill="none"
                      >
                        <path
                          d="M1.5 5.2L4 7.5L8.5 2.5"
                          stroke="white"
                          strokeWidth="1.75"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    )}
                  </span>
                  <span
                    className={cn(
                      "font-medium",
                      checked ? "text-fg" : "text-fg-2"
                    )}
                  >
                    {s.label}
                  </span>
                </label>
              );
            })}
          </div>
        </Field>

        <Field label="Notas (opcional)">
          <Textarea
            value={form.notes}
            onChange={(e) => form.setNotes(e.target.value)}
            rows={3}
            placeholder="Comentarios para el equipo..."
          />
        </Field>
      </Modal.Body>
      <Modal.Footer>
        <Button
          variant="secondary"
          onClick={() => onOpenChange(false)}
          disabled={form.submitting}
        >
          Cancelar
        </Button>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={form.submitting}
        >
          {form.submitting ? "Generando..." : "Generar"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

interface PillGroupProps<T extends string> {
  options: { value: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
}

function PillGroup<T extends string>({
  options,
  value,
  onChange,
}: PillGroupProps<T>) {
  return (
    <div className="flex gap-1.5 flex-wrap">
      {options.map((o) => {
        const active = value === o.value;
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cn(
              "px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-colors cursor-pointer",
              active
                ? "bg-ink text-white"
                : "bg-surface-2 text-fg-2 hover:bg-bg-2 hover:text-fg"
            )}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
