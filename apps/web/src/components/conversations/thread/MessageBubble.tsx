import { cn } from "@/lib/cn";
import type { BubbleMessage, Conversation } from "@/lib/mock";

export function MessageBubble({ msg }: { msg: BubbleMessage }) {
  const isAdmin = msg.author === "admin";
  return (
    <div
      className={cn(
        "flex flex-col gap-1 max-w-[70%]",
        isAdmin ? "self-end items-end" : "self-start"
      )}
    >
      <div
        className={cn(
          "px-[18px] py-3 text-sm leading-normal",
          msg.author === "student" &&
            "bg-surface-2 text-fg rounded-[18px] rounded-bl-[4px]",
          msg.author === "bot" &&
            "bg-blue-soft text-fg rounded-[18px] rounded-bl-[4px]",
          isAdmin && "bg-primary text-white rounded-[18px] rounded-br-[4px]"
        )}
      >
        {renderText(msg.text)}
      </div>
      <div className="font-mono text-[10px] text-muted flex gap-1.5 px-2">
        {msg.author === "bot" && (
          <>
            <span>bot · {msg.time}</span>
            {msg.source && <span>· {msg.source}</span>}
          </>
        )}
        {msg.author === "student" && (
          <>
            <span>{msg.time}</span>
            {msg.intent && (
              <>
                <span>·</span>
                <span
                  className={
                    msg.intent.score < 0.55
                      ? "text-primary font-semibold"
                      : ""
                  }
                >
                  {msg.intent.name} · {msg.intent.score.toFixed(2)}
                  {msg.intent.score < 0.55 && " ⚠"}
                </span>
              </>
            )}
          </>
        )}
        {isAdmin && (
          <span>
            admin · {msg.adminName ?? "Renzo"} · {msg.time}
          </span>
        )}
      </div>
    </div>
  );
}

function renderText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i}>{p.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{p}</span>
    )
  );
}

export function StatusLabel({ status }: { status: Conversation["status"] }) {
  const map: Record<Conversation["status"], string> = {
    escalated: "escalada",
    active: "activa",
    closed: "cerrada",
    pending: "pendiente",
  };
  return <>{map[status]}</>;
}
