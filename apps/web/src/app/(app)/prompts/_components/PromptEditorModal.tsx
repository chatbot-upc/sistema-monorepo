"use client";

import { useEffect, useRef, useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Textarea } from "@/components/ui/Textarea";
import { useToast } from "@/components/ui/ToastProvider";
import type { PromptVersion } from "@/lib/api/prompts";
import {
  createPromptVersionAction,
  updatePromptVersionAction,
} from "../_actions/prompts";

interface PromptEditorModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  version: PromptVersion | null;
}

export function PromptEditorModal({
  open,
  onOpenChange,
  version,
}: PromptEditorModalProps) {
  const { toast } = useToast();
  const isEdit = version !== null;
  const [content, setContent] = useState(version?.content ?? "");
  const [submitting, setSubmitting] = useState(false);

  const cancelRef = useRef(false);
  useEffect(() => {
    if (open) {
      cancelRef.current = false;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setContent(version?.content ?? "");
      setSubmitting(false);
      return () => {
        cancelRef.current = true;
      };
    }
  }, [open, version]);

  const valid = content.trim().length >= 20;

  const handleSubmit = async () => {
    if (!valid) {
      toast.error("El prompt debe tener al menos 20 caracteres");
      return;
    }
    setSubmitting(true);
    const result = isEdit
      ? await updatePromptVersionAction(version.id, content)
      : await createPromptVersionAction(content);
    if (cancelRef.current) return;
    setSubmitting(false);

    if (result.ok) {
      toast.success(
        isEdit
          ? `v${version.version} actualizada`
          : `v${result.data.version} creada`,
        {
          description: isEdit
            ? version.active
              ? "El bot ya usa el contenido editado."
              : "Cambios guardados."
            : "Actívala cuando quieras que el bot la use.",
        },
      );
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
        title={isEdit ? `Editar v${version.version}` : "Nueva versión"}
        description="El system prompt define la personalidad y reglas del agente. Markdown soportado."
      />
      <Modal.Body>
        <Field label="Contenido del prompt">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={18}
            placeholder="Eres el asistente virtual de matrícula de la UPC..."
            className="font-mono text-[12.5px] leading-relaxed"
            autoFocus
          />
          <span className="text-[11px] text-muted">
            {content.trim().length} caracteres
          </span>
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
              : "Crear versión"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
