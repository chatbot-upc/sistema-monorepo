"use client";

import { useState } from "react";
import { Textarea } from "@/components/ui/Textarea";
import { useDebouncedSave } from "@/lib/useDebouncedSave";
import { saveNotes } from "@/lib/mock";
import { Block } from "./Block";

interface NotesSectionProps {
  conversationId: string;
  notes: string;
}

export function NotesSection({ conversationId, notes }: NotesSectionProps) {
  const [local, setLocal] = useState(notes);

  // Reset del borrador local al cambiar de conversacion. Patron oficial de React
  // (ajustar estado durante el render con un rastreador de valor previo), en vez
  // de useEffect. Ref: react.dev "you might not need an effect" / Vercel
  // rerender-derived-state-no-effect.
  const [prevId, setPrevId] = useState(conversationId);
  if (prevId !== conversationId) {
    setPrevId(conversationId);
    setLocal(notes);
  }

  useDebouncedSave(conversationId, local, saveNotes, 800);

  return (
    <Block title="Notas internas">
      <Textarea
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        rows={4}
        placeholder="Anotaciones para el equipo..."
        className="text-xs leading-relaxed"
        maxLength={500}
        showCounter
      />
      <div className="text-[10px] text-muted mt-1.5 font-mono">
        Auto-guardado · 800ms
      </div>
    </Block>
  );
}
