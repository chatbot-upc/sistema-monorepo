import type { ReactNode } from "react";

interface BlockAction {
  label?: string;
  onClick?: () => void;
  renderTrigger?: ReactNode;
}

interface BlockProps {
  title: string;
  action?: BlockAction;
  children: ReactNode;
}

export function Block({ title, action, children }: BlockProps) {
  return (
    <section>
      <header className="flex justify-between items-center mb-3.5">
        <h4 className="text-[11px] font-semibold uppercase tracking-[0.6px] text-muted">
          {title}
        </h4>
        {action?.renderTrigger ??
          (action?.label && (
            <button
              type="button"
              onClick={action.onClick}
              className="text-[11px] font-medium text-fg-2 hover:text-primary transition-colors cursor-pointer"
            >
              {action.label}
            </button>
          ))}
      </header>
      {children}
    </section>
  );
}
