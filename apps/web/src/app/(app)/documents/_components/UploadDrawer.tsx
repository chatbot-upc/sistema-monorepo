"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { FileDrop } from "@/components/ui/FileDrop";
import { useToast } from "@/components/ui/ToastProvider";
import { uploadDocumentAction } from "../_actions/documents";

interface UploadDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function UploadDrawer({ open, onOpenChange }: UploadDrawerProps) {
  const { toast } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [isPending, startTransition] = useTransition();

  const reset = () => setFiles([]);

  const handleSubmit = () => {
    if (files.length === 0) {
      toast.error("Selecciona un archivo para subir");
      return;
    }
    const file = files[0];
    const fd = new FormData();
    fd.set("file", file);
    fd.set("source_type", "upload");

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
