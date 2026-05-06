import { Block } from "./Block";
import { cn } from "@/lib/cn";

type HistoryTone = "closed" | "escalated" | "bot";

interface HistoryEntry {
  tone: HistoryTone;
  title: string;
  when: string;
}

const HISTORY_SAMPLE: HistoryEntry[] = [
  {
    tone: "closed",
    title: "Consulta sobre fechas de matrícula",
    when: "14 abr · 18:42 · resuelta por bot",
  },
  {
    tone: "escalated",
    title: "Cargo extra no identificado",
    when: "02 abr · 11:15 · escalada → cerrada",
  },
  {
    tone: "bot",
    title: "Cronograma de exámenes parciales",
    when: "28 mar · 09:30 · resuelta por bot",
  },
];

export function HistorySection() {
  return (
    <Block
      title={`Historial · ${HISTORY_SAMPLE.length + 1} conversaciones`}
      action={{ label: "Ver todas" }}
    >
      <div className="flex flex-col gap-1.5">
        {HISTORY_SAMPLE.map((h) => (
          <HistoryItem key={h.title} {...h} />
        ))}
      </div>
    </Block>
  );
}

function HistoryItem({ tone, title, when }: HistoryEntry) {
  const dotColor = {
    closed: "bg-success",
    escalated: "bg-primary",
    bot: "bg-blue",
  }[tone];

  return (
    <div className="flex gap-3 py-2.5 px-3 bg-surface-2 rounded-xl">
      <span className={cn("w-2 h-2 rounded-full mt-1.5 shrink-0", dotColor)} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-semibold leading-snug">{title}</div>
        <div className="font-mono text-[10px] text-muted mt-0.5">{when}</div>
      </div>
    </div>
  );
}
