import { FileText, UploadCloud } from "lucide-react";
import { Card } from "@/components/ui/Card";

interface DocumentsStatsProps {
  indexed: number;
  indexing: number;
  totalChunks: number;
}

export function DocumentsStats({
  indexed,
  indexing,
  totalChunks,
}: DocumentsStatsProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <StatCard
        color="mint"
        textColor="text-success"
        icon={<FileText size={20} strokeWidth={2} />}
        label="Indexados"
        value={indexed}
      />
      <StatCard
        color="amber"
        textColor="text-amber-fg"
        icon={<UploadCloud size={20} strokeWidth={2} />}
        label="Procesando"
        value={indexing}
      />
      <StatCard
        color="blue"
        textColor="text-blue"
        icon={<span className="font-mono font-bold">#</span>}
        label="Total chunks"
        value={totalChunks}
      />
    </div>
  );
}

function StatCard({
  color,
  textColor,
  icon,
  label,
  value,
}: {
  color: "mint" | "amber" | "blue";
  textColor: string;
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  const bg = {
    mint: "bg-mint-soft",
    amber: "bg-amber-soft",
    blue: "bg-blue-soft",
  }[color];
  return (
    <Card className="flex items-center gap-4 p-5">
      <div
        className={`w-12 h-12 rounded-2xl ${bg} ${textColor} flex items-center justify-center`}
      >
        {icon}
      </div>
      <div>
        <div className="text-[11px] uppercase tracking-[0.6px] font-semibold text-muted">
          {label}
        </div>
        <div className="text-2xl font-bold tabular leading-tight">{value}</div>
      </div>
    </Card>
  );
}
