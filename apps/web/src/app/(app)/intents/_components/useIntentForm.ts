"use client";

import { useEffect, useState } from "react";
import type { Intent } from "@/lib/mock";

export interface IntentDraft {
  name: string;
  threshold: number;
  active: boolean;
  samplesText: string;
}

const EMPTY: IntentDraft = {
  name: "",
  threshold: 0.65,
  active: true,
  samplesText: "",
};

const fromIntent = (i: Intent): IntentDraft => ({
  name: i.name,
  threshold: i.threshold,
  active: i.active,
  samplesText: i.samples.join("\n"),
});

export function useIntentForm(intent: Intent | null, open: boolean) {
  const [draft, setDraft] = useState<IntentDraft>(
    intent ? fromIntent(intent) : EMPTY
  );
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
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
