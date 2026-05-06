import type { ReactNode } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "./Card";
import { cn } from "@/lib/cn";

type TrendDirection = "up" | "down";
type TrendTone = "success" | "primary";

interface Trend {
  text: string;
  direction: TrendDirection;
  tone?: TrendTone;
}

interface MiniStatProps {
  label: string;
  value: ReactNode;
  trend?: Trend;
}

export function MiniStat({ label, value, trend }: MiniStatProps) {
  const Icon = trend?.direction === "down" ? TrendingDown : TrendingUp;
  const toneClass =
    trend?.tone === "primary" ? "text-primary" : "text-success";

  return (
    <Card className="p-5">
      <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
        {label}
      </div>
      <div className="text-[28px] font-semibold tracking-[-0.6px] tabular leading-none mt-2">
        {value}
      </div>
      {trend ? (
        <div
          className={cn(
            "font-mono text-[12px] font-medium mt-2 flex items-center gap-1",
            toneClass
          )}
        >
          <Icon size={12} strokeWidth={2.5} />
          {trend.text}
        </div>
      ) : null}
    </Card>
  );
}
