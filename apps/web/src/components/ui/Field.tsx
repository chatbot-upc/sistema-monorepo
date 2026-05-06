import { Children, cloneElement, isValidElement, useId } from "react";
import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface FieldProps {
  label: string;
  children: ReactNode;
  className?: string;
}

/**
 * Form field wrapper que asocia el label con el control via htmlFor.
 * Cuando el children es un único ReactElement, le inyectamos un `id`
 * generado con useId() (sólo si no trae uno propio), y el `<label>`
 * lo apunta con htmlFor. Para children no-form (grids, botones custom),
 * el id se inyecta igual pero el label simplemente no hace nada al
 * clickearse — no es regresión vs el span anterior.
 */
export function Field({ label, children, className }: FieldProps) {
  const id = useId();

  let renderedChildren: ReactNode = children;
  if (
    isValidElement<{ id?: string }>(children) &&
    Children.count(children) === 1
  ) {
    if (children.props.id === undefined) {
      renderedChildren = cloneElement(children, { id });
    }
  }

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <label
        htmlFor={id}
        className="text-[11px] font-semibold uppercase tracking-wide text-muted"
      >
        {label}
      </label>
      {renderedChildren}
    </div>
  );
}
