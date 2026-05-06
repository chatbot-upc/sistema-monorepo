"use client";

import { useState } from "react";

export type RangePreset = "7d" | "30d" | "thisMonth" | "lastMonth";
export type ReportFormat = "pdf" | "excel" | "csv";

interface ReportFormState {
  range: RangePreset;
  setRange: (v: RangePreset) => void;
  format: ReportFormat;
  setFormat: (v: ReportFormat) => void;
  sections: Set<string>;
  toggleSection: (key: string) => void;
  notes: string;
  setNotes: (v: string) => void;
  submitting: boolean;
  setSubmitting: (v: boolean) => void;
}

export function useReportForm(): ReportFormState {
  const [range, setRange] = useState<RangePreset>("30d");
  const [format, setFormat] = useState<ReportFormat>("pdf");
  const [sections, setSections] = useState<Set<string>>(
    new Set(["intenciones", "conversaciones", "satisfaccion"])
  );
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const toggleSection = (key: string) => {
    setSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return {
    range,
    setRange,
    format,
    setFormat,
    sections,
    toggleSection,
    notes,
    setNotes,
    submitting,
    setSubmitting,
  };
}
