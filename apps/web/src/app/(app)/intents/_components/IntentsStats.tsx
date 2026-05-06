"use client";

import { MiniStat } from "@/components/ui/MiniStat";
import type { Intent } from "@/lib/mock";

interface IntentsStatsProps {
  intents: Intent[];
}

export function IntentsStats({ intents }: IntentsStatsProps) {
  const total = intents.length;
  const active = intents.filter((i) => i.active).length;
  const examples = intents.reduce((acc, i) => acc + i.examples, 0);
  const avgThreshold =
    total === 0
      ? 0
      : intents.reduce((acc, i) => acc + i.threshold, 0) / total;

  return (
    <div className="grid grid-cols-4 gap-4">
      <MiniStat label="Total" value={total.toString()} />
      <MiniStat label="Activas" value={active.toString()} />
      <MiniStat label="Ejemplos" value={examples.toString()} />
      <MiniStat label="Umbral promedio" value={avgThreshold.toFixed(2)} />
    </div>
  );
}
