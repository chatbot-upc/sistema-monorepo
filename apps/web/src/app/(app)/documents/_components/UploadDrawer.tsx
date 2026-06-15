"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { FileDrop } from "@/components/ui/FileDrop";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/ToastProvider";
import type { ProgramOption } from "@/lib/api/documents";
import { uploadDocumentAction } from "../_actions/documents";

interface UploadDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  programOptions: ProgramOption[];
}

// "" = General (todas las carreras) → el backend lo guarda como NULL.
const GENERAL = "";

export function UploadDrawer({
  open,
  onOpenChange,
  programOptions,
}: UploadDrawerProps) {
  const { toast } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [program, setProgram] = useState<string>(GENERAL);
  const [isPending, startTransition] = useTransition();

  const selectOptions = [
    { value: GENERAL, label: "General (todas las carreras)" },
    ...programOptions,
  ];

  const reset = () => {
    setFiles([]);
    setProgram(GENERAL);
  };

  const handleSubmit = () => {
    if (files.length === 0) {
      toast.error("Selecciona un archivo para subir");
      return;
    }
    const file = files[0];
    const fd = new FormData();
    fd.set("file", file);
    fd.set("source_type", "upload");
    fd.set("program", program);

    startTransition(async () => {
      const res = await uploadDocumentAction(fd);
      if (res.ok) {
        toast.success("Documento subido", {
          description: `${res.data.title} se está indexando.`,
        });
        reset();
        onOpenChange(false);
        return;
      }
      if (res.code === "duplicate") {
        toast.error("Documento duplicado", {
          description:
            "Ya existe un documento con el mismo contenido (sha256). Quita el archivo o elige otro.",
        });
        return;
      }
      toast.error("No se pudo subir", { description: res.error });
    });
  };

  return (
    <Drawer
      open={open}
      onOpenChange={(v) => {
        if (isPending) return;
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <Drawer.Header
        title="Subir documento"
        description="Añade un PDF a la base de conocimiento. Se indexa en segundo plano."
      />
      <Drawer.Body className="flex flex-col gap-5">
        <FileDrop
          files={files}
          onChange={setFiles}
          accept=".pdf"
          maxSizeMB={10}
          onError={(msg) =>
            toast.error("Archivo no válido", { description: msg })
          }
        />
        <div className="flex flex-col gap-2">
          <label className="text-[13px] font-medium text-fg-2">
            Programa / carrera
          </label>
          <Select
            options={selectOptions}
            value={program}
            onChange={setProgram}
            placeholder="General (todas las carreras)"
            align="start"
          />
          <p className="text-[11px] text-muted">
            Si es una malla de carrera, elige cuál: el bot la usará solo con
            alumnos de ese programa. Para reglamentos, fechas o becas, deja{" "}
            <span className="font-medium">General</span>.
          </p>
        </div>
      </Drawer.Body>
      <Drawer.Footer>
        <Button
          variant="secondary"
          onClick={() => {
            reset();
            onOpenChange(false);
          }}
          disabled={isPending}
        >
          Cancelar
        </Button>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={isPending || files.length === 0}
        >
          {isPending ? "Subiendo…" : "Subir e indexar"}
        </Button>
      </Drawer.Footer>
    </Drawer>
  );
}
