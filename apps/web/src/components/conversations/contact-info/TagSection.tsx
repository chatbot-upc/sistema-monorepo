"use client";

import { useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { Dropdown } from "@/components/ui/Dropdown";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/ToastProvider";
import { addTag, removeTag } from "@/lib/mock";
import { cn } from "@/lib/cn";
import { Block } from "./Block";

const TAG_TONES = ["blue", "amber", "violet", "mint"] as const;
type TagTone = (typeof TAG_TONES)[number];

const SUGGESTED_TAGS = [
  "matrícula",
  "pago pendiente",
  "regular",
  "ingreso",
  "becado",
  "rezagado",
  "morosidad",
];

const DEFAULT_TAGS = ["matrícula", "pago pendiente", "regular"];

interface TagSectionProps {
  conversationId: string;
  tags: string[];
}

export function TagSection({ conversationId, tags }: TagSectionProps) {
  const { toast } = useToast();
  const [draft, setDraft] = useState("");

  const visible = tags.length > 0 ? tags : DEFAULT_TAGS;
  const used = new Set(visible);
  const suggestable = SUGGESTED_TAGS.filter((t) => !used.has(t));
  const tone = (i: number): TagTone => TAG_TONES[i % TAG_TONES.length];

  return (
    <Block
      title="Etiquetas"
      action={
        suggestable.length > 0
          ? {
              renderTrigger: (
                <Dropdown align="end">
                  <Dropdown.Trigger>
                    <button className="text-[11px] font-medium text-fg-2 hover:text-primary transition-colors cursor-pointer">
                      + agregar
                    </button>
                  </Dropdown.Trigger>
                  <Dropdown.Content minWidth={220}>
                    <Dropdown.Label>Sugerencias</Dropdown.Label>
                    {suggestable.map((t) => (
                      <Dropdown.Item
                        key={t}
                        onSelect={() => {
                          addTag(conversationId, t);
                          toast.success(`Etiqueta "${t}" agregada`);
                        }}
                      >
                        {t}
                      </Dropdown.Item>
                    ))}
                    <Dropdown.Separator />
                    <div className="p-2 flex flex-col gap-2">
                      <Input
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        placeholder="Nueva etiqueta..."
                        className="!h-9 text-[12px]"
                      />
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() => {
                          const t = draft.trim();
                          if (!t) return;
                          addTag(conversationId, t);
                          toast.success(`Etiqueta "${t}" agregada`);
                          setDraft("");
                        }}
                        disabled={!draft.trim()}
                      >
                        Crear etiqueta
                      </Button>
                    </div>
                  </Dropdown.Content>
                </Dropdown>
              ),
            }
          : undefined
      }
    >
      <div className="flex flex-wrap gap-1.5">
        {visible.map((t, i) => (
          <Tag
            key={t}
            tone={tone(i)}
            onRemove={() => {
              removeTag(conversationId, t);
              toast.info(`Etiqueta "${t}" removida`);
            }}
          >
            {t}
          </Tag>
        ))}
      </div>
    </Block>
  );
}

function Tag({
  tone,
  children,
  onRemove,
}: {
  tone: TagTone;
  children: ReactNode;
  onRemove?: () => void;
}) {
  const tones: Record<TagTone, string> = {
    blue: "bg-blue-soft text-blue",
    amber: "bg-amber-soft text-amber-fg",
    violet: "bg-violet-soft text-violet",
    mint: "bg-mint-soft text-success",
  };
  return (
    <span
      className={cn(
        "px-2.5 py-1.5 rounded-full text-[11px] font-semibold inline-flex items-center gap-1.5",
        tones[tone]
      )}
    >
      {children}
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label="Quitar etiqueta"
          className="opacity-60 hover:opacity-100 cursor-pointer"
        >
          <X size={10} strokeWidth={2.5} />
        </button>
      )}
    </span>
  );
}
