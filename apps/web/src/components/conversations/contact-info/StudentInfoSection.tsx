import { Block } from "./Block";
import { cn } from "@/lib/cn";
import type { Conversation } from "@/lib/mock";

interface StudentInfoSectionProps {
  conversation: Conversation;
  onEdit: () => void;
}

export function StudentInfoSection({
  conversation,
  onEdit,
}: StudentInfoSectionProps) {
  return (
    <Block
      title="Información del estudiante"
      action={{ label: "Editar", onClick: onEdit }}
    >
      <div className="grid grid-cols-2 gap-3.5">
        <Field label="ID UPC" value={conversation.studentId ?? "—"} mono />
        <Field label="Ciclo" value={conversation.cycle ?? "—"} />
        <Field label="Carrera" value={conversation.career ?? "—"} full />
        <Field label="Email" value={conversation.email ?? "—"} mono full />
      </div>
    </Block>
  );
}

function Field({
  label,
  value,
  mono,
  full,
}: {
  label: string;
  value: string;
  mono?: boolean;
  full?: boolean;
}) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="text-[11px] text-muted mb-0.5">{label}</div>
      <div
        className={cn(
          "text-[13px] font-medium",
          mono && "font-mono text-xs"
        )}
      >
        {value}
      </div>
    </div>
  );
}
