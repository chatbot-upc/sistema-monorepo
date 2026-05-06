import { cn } from "@/lib/cn";

type Color = "mint" | "blue" | "primary" | "amber" | "violet" | "coral";

interface MiniBarsProps {
  heights: number[];
  highlightAt?: number;
  color?: Color;
  className?: string;
}

const colorClass: Record<Color, string> = {
  mint: "bg-mint",
  blue: "bg-blue",
  primary: "bg-primary",
  amber: "bg-amber",
  violet: "bg-violet",
  coral: "bg-coral",
};
const softClass: Record<Color, string> = {
  mint: "bg-mint-soft",
  blue: "bg-blue-soft",
  primary: "bg-primary-soft",
  amber: "bg-amber-soft",
  violet: "bg-violet-soft",
  coral: "bg-coral-soft",
};

export function MiniBars({
  heights,
  highlightAt,
  color = "mint",
  className,
}: MiniBarsProps) {
  const max = Math.max(...heights);
  return (
    <div className={cn("flex items-end gap-[3px] h-[120px] px-1 py-2", className)}>
      {heights.map((h, i) => {
        const pct = (h / max) * 100;
        const isPeak = i === highlightAt;
        const isMid = !isPeak && pct > 60;
        return (
          <div
            key={i}
            className={cn(
              "flex-1 rounded-t-[3px]",
              isPeak ? "bg-ink" : isMid ? colorClass[color] : softClass[color]
            )}
            style={{ height: `${pct}%` }}
          />
        );
      })}
    </div>
  );
}
