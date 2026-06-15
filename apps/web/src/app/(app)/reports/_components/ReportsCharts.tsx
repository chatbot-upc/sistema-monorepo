"use client";

import { Card } from "@/components/ui/Card";
import { BigBars } from "@/components/charts/BigBars";
import type { DayCount, IntentSlice } from "@/lib/api/reports";

const WEEKDAY = ["D", "L", "M", "M", "J", "V", "S"];
const INTENT_COLORS = ["coral", "amber", "primary", "violet", "blue"] as const;

function dayLabel(iso: string): string {
  // `iso` es solo fecha (YYYY-MM-DD); se interpreta en local sin desfase de TZ.
  const [y, m, d] = iso.split("-").map(Number);
  return WEEKDAY[new Date(y, m - 1, d).getDay()];
}

function niceMax(v: number): number {
  if (v <= 0) return 4;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  return Math.ceil(v / pow) * pow;
}

interface Props {
  daily: DayCount[];
  intents: IntentSlice[];
  loading: boolean;
}

export function ReportsCharts({ daily, intents, loading }: Props) {
  const dailyMax = Math.max(1, ...daily.map((d) => d.count));
  const topIntents = intents.slice(0, 5).map((i, idx) => ({
    name: i.intent_name,
    value: i.count,
    color: INTENT_COLORS[idx % INTENT_COLORS.length],
  }));
  const intentsMax = niceMax(Math.max(0, ...topIntents.map((i) => i.value)));

  return (
    <>
      <Card className={loading ? "p-7 opacity-60" : "p-7"}>
        <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
          Conversaciones por día
        </h3>
        <p className="text-sm text-muted mt-1">Periodo seleccionado</p>

        {daily.length === 0 ? (
          <div className="h-[260px] flex items-center justify-center text-muted text-sm">
            Sin conversaciones en este periodo.
          </div>
        ) : (
          <div className="flex items-end gap-3 mt-8 h-[260px]">
            {daily.map((d) => {
              const barPx = Math.round((d.count / dailyMax) * 200);
              return (
                <div
                  key={d.date}
                  className="flex-1 flex flex-col items-center justify-end gap-2 min-w-0"
                  title={`${d.date}: ${d.count}`}
                >
                  <span className="text-[11px] font-mono text-muted">
                    {d.count}
                  </span>
                  <div
                    className="w-full bg-mint rounded-t-xl"
                    style={{
                      height: `${Math.max(barPx, 2)}px`,
                      backgroundImage:
                        "repeating-linear-gradient(135deg, transparent 0, transparent 4px, rgba(255,255,255,0.4) 4px, rgba(255,255,255,0.4) 5px)",
                    }}
                  />
                  <span className="font-mono text-[11px] text-muted">
                    {dayLabel(d.date)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Card className={loading ? "p-7 opacity-60" : "p-7"}>
        <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
          Intenciones más frecuentes
        </h3>
        <p className="text-sm text-muted mt-1">
          Distribución del periodo · top 5
        </p>
        <div className="mt-8">
          {topIntents.length === 0 ? (
            <div className="h-[200px] flex items-center justify-center text-muted text-sm">
              Sin intenciones detectadas en este periodo.
            </div>
          ) : (
            <BigBars data={topIntents} yMax={intentsMax} />
          )}
        </div>
      </Card>
    </>
  );
}
