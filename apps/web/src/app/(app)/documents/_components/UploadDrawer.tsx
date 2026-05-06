"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Field } from "@/components/ui/Field";
import { FileDrop } from "@/components/ui/FileDrop";
import { Select, type SelectOption } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import { addDocument } from "@/lib/mock";
import type { DocType } from "./useDocumentFilters";

const TYPE_OPTIONS: SelectOption<DocType>[] = [
  { value: "PDF", label: "PDF" },
  { value: "MD", label: "Markdown" },
  { value: "TXT", label: "Texto" },
];

interface UploadDrawerProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
}

export function UploadDrawer({ open, onOpenChange }: UploadDrawerProps) {
  const { toast } = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [type, setType] = useState<DocType>("PDF");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const reset = () => {
    setFiles([]);
    setDescription("");
    setTags("");
    setProgress(null);
  };

  // Cleanup any pending interval on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const handleSubmit = async () => {
    if (files.length === 0) {
      toast.error("Selecciona un archivo para subir");
      return;
    }
    setProgress(0);
    await new Promise<void>((resolve) => {
      let p = 0;
      intervalRef.current = setInterval(() => {
        p += Math.random() * 18 + 8;
        if (p >= 100) {
          p = 100;
          setProgress(100);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          resolve();
        } else {
          setProgress(Math.round(p));
        }
      }, 110);
    });

    const f = files[0];
    addDocument({
      name: f.name,
      type,
      size: formatSize(f.size),
      status: "indexing",
      indexedAt: null,
      chunks: 0,
    });
    toast.success("Documento subido", {
      description: `${f.name} se está indexando.`,
    });
    reset();
    onOpenChange(false);
  };

  const submitting = progress !== null;

  return (
    <Drawer
      open={open}
      onOpenChange={(v) => {
        if (submitting) return;
        if (!v) reset();
        onOpenChange(v);
      }}
    >
      <Drawer.Header
        title="Subir documento"
        description="Añade una fuente al RAG. Se indexará automáticamente."
      />
      <Drawer.Body className="flex flex-col gap-5">
        <FileDrop
          files={files}
          onChange={setFiles}
          accept=".pdf,.md,.txt"
          maxSizeMB={10}
          onError={(msg) =>
            toast.error("Archivo no válido", { description: msg })
          }
        />

        <Field label="Tipo">
          <Select
            options={TYPE_OPTIONS}
            value={type}
            onChange={setType}
            className="w-full justify-between"
          />
        </Field>

        <Field label="Descripción (opcional)">
          <Input
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Resumen breve del contenido..."
          />
        </Field>

        <Field label="Etiquetas (separadas por coma)">
          <Textarea
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            rows={2}
            placeholder="matricula, costos, 2026"
            maxLength={120}
            showCounter
          />
        </Field>

        {progress !== null && (
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between text-[12px] text-fg-2">
              <span className="font-medium">Subiendo</span>
              <span className="font-mono">{progress}%</span>
            </div>
            <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-150"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </Drawer.Body>
      <Drawer.Footer>
        <Button
          variant="secondary"
          onClick={() => {
            reset();
            onOpenChange(false);
          }}
          disabled={submitting}
        >
          Cancelar
        </Button>
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={submitting || files.length === 0}
        >
          {submitting ? "Subiendo..." : "Subir e indexar"}
        </Button>
      </Drawer.Footer>
    </Drawer>
  );
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
