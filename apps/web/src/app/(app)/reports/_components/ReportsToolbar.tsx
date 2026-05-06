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

interface ReportsToolbarProps {
  range: DateRange;
  onRangeChange: (r: DateRange) => void;
}

export function ReportsToolbar({
  range,
  onRangeChange,
}: ReportsToolbarProps) {
  const { toast } = useToast();

  const exportAs = (format: "pdf" | "excel" | "csv") => {
    toast.success(`Exportando ${format.toUpperCase()}`, {
      description: `Reporte del ${formatShort(range.start)} al ${formatShort(range.end)} en cola.`,
      action: {
        label: "Ver descargas",
        onClick: () => toast.info("Abriendo bandeja de descargas..."),
      },
    });
  };

  return (
    <Card className="flex items-center gap-3 p-4">
      <DateRangePicker value={range} onChange={onRangeChange} />
      <div className="ml-auto">
        <Dropdown align="end">
          <Dropdown.Trigger>
            <Button variant="dark" size="lg">
              <Download size={16} strokeWidth={2.5} />
              Exportar
            </Button>
          </Dropdown.Trigger>
          <Dropdown.Content>
            <Dropdown.Item
              icon={<FileText size={14} strokeWidth={2} />}
              onSelect={() => exportAs("pdf")}
            >
              PDF · Reporte ejecutivo
            </Dropdown.Item>
            <Dropdown.Item
              icon={<FileSpreadsheet size={14} strokeWidth={2} />}
              onSelect={() => exportAs("excel")}
            >
              Excel · Datos tabulares
            </Dropdown.Item>
            <Dropdown.Item
              icon={<FileCode size={14} strokeWidth={2} />}
              onSelect={() => exportAs("csv")}
            >
              CSV · Crudo, máx detalle
            </Dropdown.Item>
          </Dropdown.Content>
        </Dropdown>
      </div>
    </Card>
  );
}
