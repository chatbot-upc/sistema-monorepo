"use client";

import { useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { UploadCloud, X, FileText } from "lucide-react";
import { cn } from "@/lib/cn";

interface FileDropProps {
  accept?: string;
  maxSizeMB?: number;
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
  onError?: (msg: string) => void;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileDrop({
  accept = ".pdf,.md,.txt",
  maxSizeMB = 10,
  multiple = false,
  files,
  onChange,
  onError,
}: FileDropProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [active, setActive] = useState(false);

  const validate = (incoming: File[]): File[] => {
    const max = maxSizeMB * 1024 * 1024;
    const valid: File[] = [];
    for (const f of incoming) {
      if (f.size > max) {
        onError?.(`"${f.name}" supera ${maxSizeMB} MB`);
        continue;
      }
      valid.push(f);
    }
    return valid;
  };

  const handleFiles = (incoming: FileList | File[]) => {
    const arr = Array.from(incoming);
    const valid = validate(arr);
    if (valid.length === 0) return;
    onChange(multiple ? [...files, ...valid] : valid.slice(0, 1));
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setActive(false);
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setActive(true);
  };

  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setActive(false);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) handleFiles(e.target.files);
    e.target.value = "";
  };

  const remove = (idx: number) => {
    const next = files.slice();
    next.splice(idx, 1);
    onChange(next);
  };

  return (
    <div className="flex flex-col gap-3">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={cn(
          "border-2 border-dashed rounded-2xl p-8 flex flex-col items-center gap-2 text-center cursor-pointer transition-colors outline-none",
          "focus-visible:border-primary focus-visible:bg-primary-soft/30",
          active
            ? "border-primary bg-primary-soft/50"
            : "border-line-2 bg-surface-2 hover:border-primary/40 hover:bg-primary-soft/20"
        )}
      >
        <UploadCloud size={32} className="text-muted" strokeWidth={1.75} />
        <div className="text-[14px] font-semibold text-fg">
          Arrastra un archivo o haz clic para elegir
        </div>
        <div className="text-xs text-muted">
          {accept.split(",").join(" · ")} · máx {maxSizeMB} MB
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={onPick}
          className="hidden"
        />
      </div>

      {files.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {files.map((f, i) => (
            <div
              key={`${f.name}-${i}`}
              className="flex items-center gap-3 px-3 py-2 bg-surface-2 rounded-xl"
            >
              <div className="w-9 h-9 rounded-lg bg-blue-soft text-blue flex items-center justify-center shrink-0">
                <FileText size={16} strokeWidth={2} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-medium truncate">{f.name}</div>
                <div className="font-mono text-[10px] text-muted">
                  {formatBytes(f.size)}
                </div>
              </div>
              <button
                type="button"
                onClick={() => remove(i)}
                aria-label={`Quitar ${f.name}`}
                className="w-7 h-7 rounded-full hover:bg-bg-2 text-muted hover:text-fg-2 flex items-center justify-center shrink-0 cursor-pointer transition-colors"
              >
                <X size={14} strokeWidth={2} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
