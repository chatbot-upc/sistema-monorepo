"use client";

import { useEffect, useState } from "react";
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

  // Sync local with store when conversationId or stored notes change externally
  useEffect(() => {
    setLocal(notes);
  }, [conversationId, notes]);

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
