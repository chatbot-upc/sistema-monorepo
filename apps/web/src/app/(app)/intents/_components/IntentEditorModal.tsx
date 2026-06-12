"use client";

import { useEffect, useRef } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/ToastProvider";
import { cn } from "@/lib/cn";
import type { IntentRead } from "@/lib/api/intents";
import { createIntentAction, updateIntentAction } from "../_actions/intents";
import { useIntentForm } from "./useIntentForm";

interface IntentEditorModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  intent: IntentRead | null;
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

  // Cancel guard: si el modal se cierra mid-await, descartamos el resultado.
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
    const result = isEdit
      ? await updateIntentAction(intent.id, {
          active: draft.active,
          examples: samples,
        })
      : await createIntentAction({
          name: draft.name.trim(),
          examples: samples,
        });
    if (cancelRef.current) return;
    setSubmitting(false);

    if (result.ok) {
      toast.success(isEdit ? "Intención actualizada" : "Intención creada", {
        description: isEdit
          ? `Cambios guardados para ${intent.name}.`
          : `${draft.name.trim()} con ${samples.length} ejemplos.`,
      });
      onOpenChange(false);
    } else {
      toast.error(isEdit ? "No se pudo actualizar" : "No se pudo crear", {
        description: result.error,
      });
    }
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="lg">
      <Modal.Header
        title={isEdit ? "Editar intención" : "Nueva intención"}
        description="Define el nombre técnico y las frases de ejemplo que el clasificador SBERT usa para enrutar."
      />
      <Modal.Body>
        <Field label="Nombre técnico">
          <Input
            value={draft.name}
            onChange={(e) =>
              setDraft((d) => ({ ...d, name: e.target.value }))
            }
            placeholder="ej. costos_matricula"
            autoFocus={!isEdit}
            disabled={isEdit}
            className="font-mono"
          />
          {isEdit ? (
            <span className="text-[11px] text-muted">
              El nombre técnico no se puede cambiar (se usa internamente para
              enrutar).
            </span>
          ) : (
            <span className="text-[11px] text-muted">
              snake_case · solo a-z, 0-9 y guión bajo.
            </span>
          )}
        </Field>

        <Field label="Ejemplos (uno por línea)">
          <Textarea
            value={draft.samplesText}
            onChange={(e) =>
              setDraft((d) => ({ ...d, samplesText: e.target.value }))
            }
            rows={6}
            placeholder={
              "cuánto cuesta la matrícula\nprecio de la pensión\ncuánto pago por ciclo"
            }
            className="font-mono text-[12.5px]"
          />
          <span className="text-[11px] text-muted">
            {samples.length} ejemplo{samples.length === 1 ? "" : "s"} reconocido
            {samples.length === 1 ? "" : "s"}
          </span>
        </Field>

        <Field label="Estado">
          <button
            type="button"
            role="switch"
            aria-checked={draft.active}
            onClick={() => setDraft((d) => ({ ...d, active: !d.active }))}
            className={cn(
              "flex items-center justify-between rounded-2xl px-4 py-3 border transition-colors cursor-pointer w-full",
              draft.active
                ? "bg-primary-soft border-primary/20"
                : "bg-surface-2 border-transparent hover:bg-bg-2",
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
                draft.active ? "bg-primary" : "bg-muted-2",
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow-sm transition-transform",
                  draft.active && "translate-x-5",
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
