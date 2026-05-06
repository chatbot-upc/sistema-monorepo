"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import type { Conversation } from "@/lib/mock";

interface EditContactDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  conversation: Conversation;
}

export function EditContactDrawer({
  open,
  onOpenChange,
  conversation,
}: EditContactDrawerProps) {
  const { toast } = useToast();
  const [name, setName] = useState(conversation.name);
  const [studentId, setStudentId] = useState(conversation.studentId ?? "");
  const [career, setCareer] = useState(conversation.career ?? "");
  const [cycle, setCycle] = useState(conversation.cycle ?? "");
  const [email, setEmail] = useState(conversation.email ?? "");

  useEffect(() => {
    if (!open) return;
    setName(conversation.name);
    setStudentId(conversation.studentId ?? "");
    setCareer(conversation.career ?? "");
    setCycle(conversation.cycle ?? "");
    setEmail(conversation.email ?? "");
  }, [open, conversation]);

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <Drawer.Header
        title="Editar contacto"
        description="Actualiza la información del estudiante. Los cambios son locales en este demo."
      />
      <Drawer.Body className="flex flex-col gap-4">
        <Field label="Nombre">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label="ID UPC">
          <Input
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
            placeholder="U2021XXXX"
          />
        </Field>
        <Field label="Carrera">
          <Input
            value={career}
            onChange={(e) => setCareer(e.target.value)}
            placeholder="Ingeniería de Sistemas"
          />
        </Field>
        <Field label="Ciclo">
          <Input
            value={cycle}
            onChange={(e) => setCycle(e.target.value)}
            placeholder="6° (2026-1)"
          />
        </Field>
        <Field label="Email">
          <Input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="alumno@upc.edu.pe"
          />
        </Field>
      </Drawer.Body>
      <Drawer.Footer>
        <Button variant="secondary" onClick={() => onOpenChange(false)}>
          Cancelar
        </Button>
        <Button
          variant="primary"
          onClick={() => {
            toast.success("Datos actualizados", {
              description: "Los cambios se guardaron en el panel.",
            });
            onOpenChange(false);
          }}
        >
          Guardar
        </Button>
      </Drawer.Footer>
    </Drawer>
  );
}

