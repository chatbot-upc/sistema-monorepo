"use client";

import { useState } from "react";
import { AlertCircle } from "lucide-react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { useToast } from "./ToastProvider";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "default" | "destructive";
  onConfirm: () => void | Promise<void>;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirmar",
  cancelLabel = "Cancelar",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo completar la acción";
      toast.error("Error al confirmar", { description: message });
    } finally {
      setLoading(false);
    }
  };

  const icon =
    variant === "destructive" ? (
      <div className="w-9 h-9 rounded-full bg-primary-soft flex items-center justify-center">
        <AlertCircle size={18} className="text-primary" strokeWidth={2} />
      </div>
    ) : undefined;

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="sm">
      <Modal.Header title={title} description={description} icon={icon} />
      <Modal.Footer>
        <Button
          variant="secondary"
          onClick={() => onOpenChange(false)}
          disabled={loading}
        >
          {cancelLabel}
        </Button>
        <Button
          variant="primary"
          onClick={handleConfirm}
          disabled={loading}
        >
          {loading ? "Procesando..." : confirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}
