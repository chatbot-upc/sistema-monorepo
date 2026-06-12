"use client";

import { useEffect, useState } from "react";
import type { IntentRead } from "@/lib/api/intents";

export interface IntentDraft {
  name: string;
  active: boolean;
  samplesText: string;
}

const EMPTY: IntentDraft = {
  name: "",
  active: true,
  samplesText: "",
};

const fromIntent = (i: IntentRead): IntentDraft => ({
  name: i.name,
  active: i.active,
  samplesText: i.examples.join("\n"),
});

export function useIntentForm(intent: IntentRead | null, open: boolean) {
  const [draft, setDraft] = useState<IntentDraft>(
    intent ? fromIntent(intent) : EMPTY,
  );
  const [submitting, setSubmitting] = useState(false);

  // Reset del draft editable cada vez que el modal abre (o cambia el intent).
  // No es estado derivado: el usuario lo edita, así que se siembra desde props
  // al abrir y luego es independiente. setState-in-effect es el patrón correcto
  // para "reset form on open".
  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDraft(intent ? fromIntent(intent) : EMPTY);
    setSubmitting(false);
  }, [open, intent]);

  const samples = draft.samplesText
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  const valid = draft.name.trim().length > 0 && samples.length > 0;

  return {
    draft,
    setDraft,
    samples,
    submitting,
    setSubmitting,
    valid,
  };
}
