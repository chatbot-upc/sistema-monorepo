import { cn } from "@/lib/cn";
import type { ReactNode } from "react";
import { Card } from "./Card";
import { Equalizer } from "./Equalizer";

type StatColor = "mint" | "primary" | "amber" | "blue";

interface StatCardProps {
  label: string;
  value: string;
  icon: ReactNode;
  color: StatColor;
  ratio?: number;
  legend?: { left: string; right: string };
  breakdown?: { left: string; right: string };
}

const iconBg: Record<StatColor, string> = {
  mint: "bg-mint-soft text-success",
  primary: "bg-primary-soft text-primary",
  amber: "bg-amber-soft text-amber-fg",
  blue: "bg-blue-soft text-blue",
};

export function StatCard({
  label,
  value,
  icon,
  color,
  ratio = 0.85,
  legend,
  breakdown,
}: StatCardProps) {
  return (
    <Card className="flex flex-col gap-4 p-6" variant="flush">
      <div className="flex items-start justify-between p-0">
        <div>
          <div className="text-[13px] text-muted">{label}</div>
          <div className="text-[28px] font-semibold tracking-[-0.6px] leading-none mt-2 tabular">
            {value}
          </div>
        </div>
        <div
          className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0",
            iconBg[color]
          )}
        >
          {icon}
        </div>
      </div>

      {legend && (
        <div className="flex justify-between text-[12px] text-muted">
          <span>{legend.left}</span>
          <span>{legend.right}</span>
        </div>
      )}

      <Equalizer color={color} ratio={ratio} />

      {breakdown && (
        <div className="flex justify-between text-[13px] font-mono text-fg">
          <span>{breakdown.left}</span>
          <span>{breakdown.right}</span>
        </div>
      )}
    </Card>
  );
}
