"use client";

import { MiniStat } from "@/components/ui/MiniStat";
import type { ReportSummary } from "@/lib/api/reports";

function fmt(n: number): string {
  return n.toLocaleString("es-PE");
}

function signed(n: number): string {
  return n >= 0 ? `+${n}` : `${n}`;
}

interface Props {
  summary: ReportSummary | null;
  loading: boolean;
}

export function ReportsSummary({ summary, loading }: Props) {
  if (!summary) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-surface rounded-3xl p-5 h-[104px] animate-pulse"
          />
        ))}
      </div>
    );
  }

  const totalTrend =
    summary.total_change_pct != null
      ? {
          text: `${signed(summary.total_change_pct)}% vs anterior`,
          direction:
            summary.total_change_pct >= 0 ? ("up" as const) : ("down" as const),
        }
      : { text: "sin periodo previo", direction: "up" as const };

  const fallbackTrend =
    summary.fallback_change_pp != null
      ? {
          text: `${signed(summary.fallback_change_pp)}pp vs anterior`,
          direction:
            summary.fallback_change_pp <= 0
              ? ("down" as const)
              : ("up" as const),
        }
      : { text: "sin periodo previo", direction: "down" as const };

  return (
    <div
      className={
        loading
          ? "grid grid-cols-4 gap-4 opacity-60"
          : "grid grid-cols-4 gap-4"
      }
    >
      <MiniStat
        label="Total conversaciones"
        value={fmt(summary.total)}
        trend={totalTrend}
      />
      <MiniStat
        label="Resueltas por bot"
        value={fmt(summary.resolved_by_bot)}
        trend={{
          text: `${summary.resolved_pct_of_total}% del total`,
          direction: "up",
        }}
      />
      <MiniStat
        label="Escaladas"
        value={fmt(summary.escalated)}
        trend={{
          text: `${summary.escalated_pct_of_total}% del total`,
          direction: "down",
          tone: "primary",
        }}
      />
      <MiniStat
        label="Tasa fallback"
        value={
          <>
            {summary.fallback_rate}
            <span className="text-2xl text-muted">%</span>
          </>
        }
        trend={fallbackTrend}
      />
    </div>
  );
}
