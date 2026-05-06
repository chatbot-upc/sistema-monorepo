import { cn } from "@/lib/cn";

type Color = "primary" | "coral" | "amber" | "violet" | "blue" | "mint";

const colorBg: Record<Color, string> = {
  primary: "bg-primary",
  coral: "bg-coral",
  amber: "bg-amber",
  violet: "bg-violet",
  blue: "bg-blue",
  mint: "bg-mint",
};

interface BigBarsProps {
  data: { name: string; value: number; color: Color }[];
  yMax?: number;
}

export function BigBars({ data, yMax = 1000 }: BigBarsProps) {
  return (
    <div className="grid grid-cols-[50px_1fr] gap-4 h-[380px] relative">
      {/* Y axis */}
      <div className="flex flex-col-reverse justify-between h-full pb-9 pt-2 font-mono text-[11px] text-muted-2">
        <span>0</span>
        <span>{yMax / 4}</span>
        <span>{yMax / 2}</span>
        <span>{(yMax / 4) * 3}</span>
        <span>{yMax >= 1000 ? `${yMax / 1000}k` : yMax}</span>
      </div>

      {/* Bars */}
      <div className="grid grid-cols-5 gap-4 h-full pb-9 relative">
        {data.map((item) => {
          const heightPct = (item.value / yMax) * 100;
          return (
            <div
              key={item.name}
              className="flex flex-col justify-end items-stretch min-w-0 text-center relative"
            >
              <span className="text-[11px] text-muted">conv</span>
              <span className="text-[18px] font-semibold tracking-[-0.2px] mt-0.5 mb-2 leading-none">
                {item.value}
              </span>
              <div
                className={cn(
                  "w-full rounded-t-xl relative",
                  colorBg[item.color]
                )}
                style={{
                  height: `${heightPct}%`,
                  backgroundImage:
                    "repeating-linear-gradient(135deg, transparent 0, transparent 4px, rgba(255,255,255,0.4) 4px, rgba(255,255,255,0.4) 5px)",
                }}
              >
                <span className="absolute -top-[3px] left-0 right-0 h-[3px] rounded-sm bg-ink" />
              </div>
            </div>
          );
        })}

        {/* X axis labels */}
        <div className="absolute bottom-0 left-0 right-0 grid grid-cols-5 gap-4 font-mono text-[11px] text-muted text-center pt-3">
          {data.map((item) => (
            <span key={item.name}>{item.name}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
