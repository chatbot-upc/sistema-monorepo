"use client";

import { Card } from "@/components/ui/Card";
import { BigBars } from "@/components/charts/BigBars";
import { topIntents } from "@/lib/mock";

const WEEK_DAYS = [
  { label: "L", value: 142 },
  { label: "M", value: 168 },
  { label: "M", value: 195 },
  { label: "J", value: 220 },
  { label: "V", value: 244 },
  { label: "S", value: 88 },
  { label: "D", value: 56 },
];

export function ReportsCharts() {
  const max = Math.max(...WEEK_DAYS.map((d) => d.value));

  return (
    <>
      <Card className="p-7">
        <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
          Conversaciones por día
        </h3>
        <p className="text-sm text-muted mt-1">Última semana</p>

        <div className="flex items-end gap-3 mt-8 h-[260px]">
          {WEEK_DAYS.map((d, i) => {
            const barPx = Math.round((d.value / max) * 200);
            return (
              <div
                key={i}
                className="flex-1 flex flex-col items-center justify-end gap-2"
              >
                <span className="text-[11px] font-mono text-muted">
                  {d.value}
                </span>
                <div
                  className="w-full bg-mint rounded-t-xl"
                  style={{
                    height: `${barPx}px`,
                    backgroundImage:
                      "repeating-linear-gradient(135deg, transparent 0, transparent 4px, rgba(255,255,255,0.4) 4px, rgba(255,255,255,0.4) 5px)",
                  }}
                />
                <span className="font-mono text-[11px] text-muted">
                  {d.label}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      <Card className="p-7">
        <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
          Intenciones más frecuentes
        </h3>
        <p className="text-sm text-muted mt-1">
          Distribución del periodo · top 5
        </p>
        <div className="mt-8">
          <BigBars data={topIntents} yMax={400} />
        </div>
      </Card>
    </>
  );
}
