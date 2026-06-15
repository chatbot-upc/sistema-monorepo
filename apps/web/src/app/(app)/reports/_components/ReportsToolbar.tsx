"use client";

import { Download, FileSpreadsheet, FileText, FileCode } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Dropdown } from "@/components/ui/Dropdown";
import {
  DateRangePicker,
  type DateRange,
} from "@/components/ui/DateRangePicker";
import { useToast } from "@/components/ui/ToastProvider";
import { formatShort } from "@/lib/dates";
import type { ReportsData } from "../_actions/reports";
import { exportCsv, exportExcel, exportPdf } from "./export";

interface ReportsToolbarProps {
  range: DateRange;
  onRangeChange: (r: DateRange) => void;
  data: ReportsData | null;
}

function isoLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function ReportsToolbar({
  range,
  onRangeChange,
  data,
}: ReportsToolbarProps) {
  const { toast } = useToast();
  const rangeLabel = `${formatShort(range.start)} → ${formatShort(range.end)}`;
  const stem = `reporte-upcbot-${isoLocal(range.start)}_${isoLocal(range.end)}`;

  const onExport = (format: "pdf" | "excel" | "csv") => {
    if (!data) {
      toast.info("Aún cargando datos del reporte…");
      return;
    }
    if (format === "csv") exportCsv(data, rangeLabel, `${stem}.csv`);
    else if (format === "excel") exportExcel(data, rangeLabel, `${stem}.xls`);
    else exportPdf(data, rangeLabel);
    toast.success(`Exportando ${format.toUpperCase()}`, {
      description: `Reporte del ${rangeLabel}.`,
    });
  };

  return (
    <Card className="flex items-center gap-3 p-4">
      <DateRangePicker value={range} onChange={onRangeChange} />
      <div className="ml-auto">
        <Dropdown align="end">
          <Dropdown.Trigger>
            <Button variant="dark" size="lg" disabled={!data}>
              <Download size={16} strokeWidth={2.5} />
              Exportar
            </Button>
          </Dropdown.Trigger>
          <Dropdown.Content>
            <Dropdown.Item
              icon={<FileText size={14} strokeWidth={2} />}
              onSelect={() => onExport("pdf")}
            >
              PDF · Reporte ejecutivo
            </Dropdown.Item>
            <Dropdown.Item
              icon={<FileSpreadsheet size={14} strokeWidth={2} />}
              onSelect={() => onExport("excel")}
            >
              Excel · Datos tabulares
            </Dropdown.Item>
            <Dropdown.Item
              icon={<FileCode size={14} strokeWidth={2} />}
              onSelect={() => onExport("csv")}
            >
              CSV · Crudo, máx detalle
            </Dropdown.Item>
          </Dropdown.Content>
        </Dropdown>
      </div>
    </Card>
  );
}
