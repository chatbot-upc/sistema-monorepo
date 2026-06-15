/* eslint-disable react-hooks/set-state-in-effect */
"use client";

import { useEffect, useState } from "react";
import type { DateRange } from "@/components/ui/DateRangePicker";
import { ReportsToolbar } from "./_components/ReportsToolbar";
import { ReportsSummary } from "./_components/ReportsSummary";
import { ReportsCharts } from "./_components/ReportsCharts";
import { fetchReportsAction, type ReportsData } from "./_actions/reports";

function isoLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function lastDays(n: number): DateRange {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - (n - 1));
  return { start, end };
}

export default function ReportsPage() {
  const [range, setRange] = useState<DateRange>(() => lastDays(7));
  const [data, setData] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    void (async () => {
      const result = await fetchReportsAction(
        isoLocal(range.start),
        isoLocal(range.end),
      );
      if (!alive) return;
      if (result.ok) setData(result.data);
      else setError(result.error);
      setLoading(false);
    })();
    return () => {
      alive = false;
    };
  }, [range]);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
          Reportes
        </h1>
        <p className="text-sm text-muted mt-2">
          Análisis histórico del chatbot · exporta a PDF, Excel o CSV
        </p>
      </header>

      <ReportsToolbar range={range} onRangeChange={setRange} data={data} />

      {error ? (
        <div className="text-sm text-primary bg-primary-soft rounded-2xl px-5 py-4">
          {error}
        </div>
      ) : (
        <>
          <ReportsSummary summary={data?.summary ?? null} loading={loading} />
          <ReportsCharts
            daily={data?.daily ?? []}
            intents={data?.intents ?? []}
            loading={loading}
          />
        </>
      )}
    </div>
  );
}
