"use client";

import { useEffect, useRef } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/ToastProvider";
import {
  addIntent,
  updateIntent,
  type Intent,
} from "@/lib/mock";
import { cn } from "@/lib/cn";
import { useIntentForm } from "./useIntentForm";

interface IntentEditorModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  intent: Intent | null;
}

export function IntentEditorModal({
  open,
  onOpenChange,
  intent,
}: IntentEditorModalProps) {
  const { toast } = useToast();
  const { draft, setDraft, samples, submitting, setSubmitting, valid } =
    useIntentForm(intent, open);
  const isEdit = intent !== null;

  // Cancel guard: si el modal se cierra mid-await (Esc, Cancel, click fuera),
  // descartamos la mutación + toast en vez de aplicarlos en background.
  // Vercel rule: rerender-use-ref-transient-values.
  const cancelRef = useRef(false);
  useEffect(() => {
    if (open) {
      cancelRef.current = false;
      return () => {
        cancelRef.current = true;
      };
    }
  }, [open]);

  const handleSubmit = async () => {
    if (!valid) {
      toast.error("Completa el nombre y al menos un ejemplo");
      return;
    }
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 350));
    if (cancelRef.current) return;
    if (isEdit) {
      updateIntent(intent.id, {
        name: draft.name.trim(),
        threshold: draft.threshold,
        active: draft.active,
        samples,
        examples: samples.length,
      });
      toast.success("Intención actualizada", {
        description: `Cambios guardados para ${draft.name.trim()}.`,
      });
    } else {
      addIntent({
        name: draft.name.trim(),
        threshold: draft.threshold,
        active: draft.active,
        samples,
        examples: samples.length,
      });
      toast.success("Intención creada", {
        description: `${draft.name.trim()} con ${samples.length} ejemplos.`,
      });
    }
    setSubmitting(false);
    onOpenChange(false);
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="lg">
      <Modal.Header
        title={isEdit ? "Editar intención" : "Nueva intención"}
        description="Define el nombre técnico, los ejemplos de entrenamiento y el umbral mínimo de confianza."
      />
      <Modal.Body>
        <Field label="Nombre técnico">
          <Input
            value={draft.name}
            onChange={(e) =>
              setDraft((d) => ({ ...d, name: e.target.value }))
            }
            placeholder="ej. costos_matricula"
            autoFocus
            className="font-mono"
          />
        </Field>

        <Field label="Ejemplos (uno por línea)">
          <Textarea
            value={draft.samplesText}
            onChange={(e) =>
              setDraft((d) => ({ ...d, samplesText: e.target.value }))
            }
            rows={6}
            placeholder={"cuánto cuesta la matrícula\nprecio de la pensión\ncuánto pago por ciclo"}
            className="font-mono text-[12.5px]"
          />
          <span className="text-[11px] text-muted">
            {samples.length} ejemplo{samples.length === 1 ? "" : "s"} reconocido
            {samples.length === 1 ? "" : "s"}
          </span>
        </Field>

        <Field label={`Umbral de confianza · ${draft.threshold.toFixed(2)}`}>
          <ThresholdSlider
            value={draft.threshold}
            onChange={(v) => setDraft((d) => ({ ...d, threshold: v }))}
          />
          <div className="flex justify-between text-[11px] text-muted font-mono">
            <span>0.00 (laxo)</span>
            <span>1.00 (estricto)</span>
          </div>
        </Field>

        <Field label="Estado">
          <button
            type="button"
            role="switch"
            aria-checked={draft.active}
            onClick={() =>
              setDraft((d) => ({ ...d, active: !d.active }))
            }
            className={cn(
              "flex items-center justify-between rounded-2xl px-4 py-3 border transition-colors cursor-pointer",
              draft.active
                ? "bg-primary-soft border-primary/20"
                : "bg-surface-2 border-transparent hover:bg-bg-2"
            )}
          >
            <div className="text-left">
              <div className="text-[13px] font-semibold text-fg">
                {draft.active ? "Activa" : "Inactiva"}
              </div>
              <div className="text-[11px] text-muted mt-0.5">
                {draft.active
                  ? "El modelo puede enrutar a esta intención."
                  : "Pausada — no se considera al clasificar."}
              </div>
            </div>
            <span
              className={cn(
                "relative w-11 h-6 rounded-full transition-colors shrink-0",
                draft.active ? "bg-primary" : "bg-muted-2"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform",
                  draft.active && "translate-x-5"
                )}
              />
            </span>
          </button>
        </Field>
      </Modal.Body>
      <Modal.Footer>
        <Button
          variant="secondary"
          onClick={() => onOpenChange(false)}
          disabled={submitting}
        >
          Cancelar
        </Button>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={submitting || !valid}
        >
          {submitting
            ? "Guardando..."
            : isEdit
              ? "Guardar cambios"
              : "Crear intención"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

interface ThresholdSliderProps {
  value: number;
  onChange: (v: number) => void;
}

function ThresholdSlider({ value, onChange }: ThresholdSliderProps) {
  const pct = Math.round(value * 100);
  return (
    <div className="relative h-6 flex items-center">
      <div className="absolute inset-x-0 h-1.5 rounded-full bg-surface-2" />
      <div
        className="absolute h-1.5 rounded-full bg-primary"
        style={{ width: `${pct}%` }}
      />
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="relative w-full h-6 appearance-none bg-transparent cursor-pointer slider-thumb"
        aria-label="Umbral de confianza"
      />
    </div>
  );
}
