"use client";

import { useState } from "react";
import type { DateRange } from "@/components/ui/DateRangePicker";
import { ReportsToolbar } from "./_components/ReportsToolbar";
import { ReportsSummary } from "./_components/ReportsSummary";
import { ReportsCharts } from "./_components/ReportsCharts";

const DEFAULT_RANGE: DateRange = {
  start: new Date(2026, 3, 21), // 21 abr 2026
  end: new Date(2026, 4, 1), //   01 may 2026
};

export default function ReportsPage() {
  const [range, setRange] = useState<DateRange>(DEFAULT_RANGE);

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

      <ReportsToolbar range={range} onRangeChange={setRange} />

      <ReportsSummary />

      <ReportsCharts />
    </div>
  );
}
