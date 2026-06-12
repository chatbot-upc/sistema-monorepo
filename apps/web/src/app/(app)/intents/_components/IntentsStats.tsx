"use client";

import { MiniStat } from "@/components/ui/MiniStat";
import type { IntentRead } from "@/lib/api/intents";

interface IntentsStatsProps {
  intents: IntentRead[];
}

export function IntentsStats({ intents }: IntentsStatsProps) {
  const total = intents.length;
  const active = intents.filter((i) => i.active).length;
  const inactive = total - active;
  const examples = intents.reduce((acc, i) => acc + i.examples.length, 0);

  return (
    <div className="grid grid-cols-4 gap-4">
      <MiniStat label="Total" value={total.toString()} />
      <MiniStat label="Activas" value={active.toString()} />
      <MiniStat label="Inactivas" value={inactive.toString()} />
      <MiniStat label="Ejemplos" value={examples.toString()} />
    </div>
  );
}
