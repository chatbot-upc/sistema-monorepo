"use client";

import { MiniStat } from "@/components/ui/MiniStat";

export function ReportsSummary() {
  return (
    <div className="grid grid-cols-4 gap-4">
      <MiniStat
        label="Total conversaciones"
        value="8,420"
        trend={{ text: "+18.2% vs anterior", direction: "up" }}
      />
      <MiniStat
        label="Resueltas por bot"
        value="7,432"
        trend={{ text: "88.3% del total", direction: "up" }}
      />
      <MiniStat
        label="Escaladas"
        value="287"
        trend={{
          text: "3.4% del total",
          direction: "down",
          tone: "primary",
        }}
      />
      <MiniStat
        label="Tasa fallback"
        value={
          <>
            8.1<span className="text-2xl text-muted">%</span>
          </>
        }
        trend={{ text: "-1.2pp vs anterior", direction: "down" }}
      />
    </div>
  );
}
