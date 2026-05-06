"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/ToastProvider";
import { addConversation, type Conversation } from "@/lib/mock";

const GRADIENTS: Conversation["gradient"][] = [
  "amber",
  "coral",
  "violet",
  "mint",
  "blue",
  "rose",
];

const TEMPLATES = [
  { value: "saludo", label: "Saludo y bienvenida" },
  { value: "matricula", label: "Información de matrícula" },
  { value: "pago", label: "Estado de pago" },
  { value: "vacio", label: "Sin plantilla" },
];

const PREVIEW_BY_TEMPLATE: Record<string, string> = {
  saludo: "(plantilla saludo enviada)",
  matricula: "(info de matrícula enviada)",
  pago: "(consulta de pago enviada)",
  vacio: "(sin mensaje inicial)",
};

interface NewConversationModalProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function NewConversationModal({
  open,
  onOpenChange,
}: NewConversationModalProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("saludo");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const trimmedPhone = phone.trim();
    const trimmedName = name.trim();
    if (!trimmedPhone) {
      toast.error("Ingresa un teléfono válido");
      return;
    }
    setSubmitting(true);
    await new Promise((r) => setTimeout(r, 350));
    const initials =
      (trimmedName || trimmedPhone)
        .split(/\s+/)
        .map((s) => s.charAt(0))
        .join("")
        .slice(0, 2)
        .toUpperCase() || "??";
    const id = `nv-${Date.now().toString(36)}`;
    const gradient = GRADIENTS[Math.floor(Math.random() * GRADIENTS.length)];
    addConversation({
      id,
      name: trimmedName || trimmedPhone,
      phone: trimmedPhone,
      preview: PREVIEW_BY_TEMPLATE[template] ?? "(sin mensaje inicial)",
      time: new Date().toLocaleTimeString("es-PE", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
      status: "active",
      gradient,
      initials,
    });
    toast.success("Conversación creada", {
      description: `Abriendo chat con ${trimmedName || trimmedPhone}.`,
    });
    setSubmitting(false);
    setPhone("");
    setName("");
    setTemplate("saludo");
    onOpenChange(false);
    router.push(`/conversations/${id}`);
  };

  return (
    <Modal open={open} onOpenChange={onOpenChange} size="sm">
      <Modal.Header
        title="Nueva conversación"
        description="Inicia un chat con un estudiante. Se enviará la plantilla seleccionada."
      />
      <Modal.Body>
        <Field label="Teléfono">
          <Input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+51 9XX XXX XXX"
            autoFocus
          />
        </Field>
        <Field label="Nombre (opcional)">
          <Input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="María Paula Rivera"
          />
        </Field>
        <Field label="Plantilla inicial">
          <Select
            options={TEMPLATES}
            value={template}
            onChange={setTemplate}
            className="w-full justify-between"
          />
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
          onClick={submit}
          disabled={submitting || !phone.trim()}
        >
          {submitting ? "Creando..." : "Iniciar conversación"}
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

