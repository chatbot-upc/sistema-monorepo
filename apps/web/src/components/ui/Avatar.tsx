import { cn } from "@/lib/cn";

type Gradient = "amber" | "coral" | "violet" | "mint" | "blue" | "rose";
type Size = "sm" | "md" | "lg" | "xl";

interface AvatarProps {
  initials: string;
  gradient?: Gradient;
  size?: Size;
  className?: string;
}

const gradients: Record<Gradient, string> = {
  amber: "bg-[linear-gradient(135deg,#FDE68A,#FBBF24)]",
  coral: "bg-[linear-gradient(135deg,#FF7A6E,#D50000)]",
  violet: "bg-[linear-gradient(135deg,#C4B5FD,#7C3AED)]",
  mint: "bg-[linear-gradient(135deg,#A7F3D0,#10B981)]",
  blue: "bg-[linear-gradient(135deg,#3B82F6,#8B5CF6)]",
  rose: "bg-[linear-gradient(135deg,#FDA4AF,#F43F5E)]",
};

const sizes: Record<Size, string> = {
  sm: "w-7 h-7 text-[11px]",
  md: "w-10 h-10 text-sm",
  lg: "w-12 h-12 text-base",
  xl: "w-[84px] h-[84px] text-[28px]",
};

export function Avatar({
  initials,
  gradient = "amber",
  size = "md",
  className,
}: AvatarProps) {
  return (
    <div
      className={cn(
        "rounded-full flex items-center justify-center text-white font-semibold flex-shrink-0",
        gradients[gradient],
        sizes[size],
        className
      )}
      style={size === "xl" ? { width: 84, height: 84, fontSize: 28 } : undefined}
    >
      {initials}
    </div>
  );
}
