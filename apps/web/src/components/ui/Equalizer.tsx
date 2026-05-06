import { cn } from "@/lib/cn";

type Color = "mint" | "primary" | "amber" | "blue" | "violet" | "coral";

interface EqualizerProps {
  color?: Color;
  ratio?: number; // 0–1 fraction of bars active
  bars?: number;
  className?: string;
}

const colorClass: Record<Color, string> = {
  mint: "bg-mint",
  primary: "bg-primary",
  amber: "bg-amber",
  blue: "bg-blue",
  violet: "bg-violet",
  coral: "bg-coral",
};

// Pseudo-random but deterministic heights so SSR matches client
function seededHeights(seed: number, n: number): number[] {
  const out: number[] = [];
  let s = seed;
  for (let i = 0; i < n; i++) {
    s = (s * 9301 + 49297) % 233280;
    out.push(0.3 + (s / 233280) * 0.7);
  }
  // simple smoothing
  for (let i = 1; i < n - 1; i++) {
    out[i] = (out[i - 1] + out[i] + out[i + 1]) / 3;
  }
  return out;
}

export function Equalizer({
  color = "mint",
  ratio = 0.85,
  bars = 32,
  className,
}: EqualizerProps) {
  const heights = seededHeights(color.charCodeAt(0) * 13, bars);
  return (
    <div className={cn("flex items-end gap-[2px] h-9 w-full", className)}>
      {heights.map((h, i) => (
        <div
          key={i}
          className={cn(
            "flex-1 rounded-[1px]",
            i / bars < ratio ? colorClass[color] : "bg-line"
          )}
          style={{ height: `${h * 100}%` }}
        />
      ))}
    </div>
  );
}
