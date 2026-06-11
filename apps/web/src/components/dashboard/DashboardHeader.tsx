"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ReportModal } from "./header/ReportModal";

export function DashboardHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="flex items-end justify-between">
      <div>
        <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
          Resumen
        </h1>
        <p className="text-sm text-muted mt-2">
          Estado del chatbot · datos del día
        </p>
      </div>
      <Button variant="primary" size="md" onClick={() => setOpen(true)}>
        <FileText size={16} strokeWidth={2} />
        Generar reporte
      </Button>

      <ReportModal open={open} onOpenChange={setOpen} />
    </header>
  );
}
