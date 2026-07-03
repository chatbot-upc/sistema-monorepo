"use client";

import { useState, useTransition } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FileDrop } from "@/components/ui/FileDrop";
import { MiniStat } from "@/components/ui/MiniStat";
import { useToast } from "@/components/ui/ToastProvider";
import type { BillingImportResult, BillingOverview } from "@/lib/api/billing";
import {
  fetchBillingOverviewAction,
  importBillingAction,
} from "../_actions/billing";

const TEMPLATE_HEADERS =
  "telefono,ciclo,numero,concepto,monto,vencimiento,estado,fecha_pago";
const TEMPLATE_SAMPLE = [
  "+51911111111,2026-1,1,Matrícula 2026-1,850.00,2026-03-15,pagado,2026-03-15",
  "+51911111111,2026-1,2,Cuota 1 - Pensión,1850.00,2026-04-15,pendiente,",
  "+51911111111,2026-1,3,Cuota 2 - Pensión,1850.00,2026-05-15,pendiente,",
];

function fmtMoney(value: number | string, currency: string): string {
  const n = Number(value);
  const prefix = currency === "PEN" ? "S/ " : `${currency} `;
  return `${prefix}${n.toLocaleString("es-PE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function downloadTemplate() {
  const csv = [TEMPLATE_HEADERS, ...TEMPLATE_SAMPLE].join("\n");
  const blob = new Blob([`﻿${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "plantilla-facturacion.csv";
  a.click();
  URL.revokeObjectURL(url);
}

interface Props {
  initialOverview: BillingOverview | null;
}

export function BillingView({ initialOverview }: Props) {
  const { toast } = useToast();
  const [overview, setOverview] = useState<BillingOverview | null>(
    initialOverview,
  );
  const [files, setFiles] = useState<File[]>([]);
  const [result, setResult] = useState<BillingImportResult | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = () => {
    if (files.length === 0) {
      toast.error("Selecciona un archivo para subir");
      return;
    }
    const fd = new FormData();
    fd.set("file", files[0]);

    startTransition(async () => {
      const res = await importBillingAction(fd);
      if (!res.ok) {
        toast.error("No se pudo cargar", { description: res.error });
        return;
      }
      setResult(res.data);
      setFiles([]);
      const { inserted, updated, skipped } = res.data;
      if (skipped > 0) {
        toast.info("Carga con observaciones", {
          description: `${inserted} nuevas, ${updated} actualizadas, ${skipped} con error.`,
        });
      } else {
        toast.success("Facturación cargada", {
          description: `${inserted} nuevas, ${updated} actualizadas.`,
        });
      }
      const fresh = await fetchBillingOverviewAction();
      if (fresh.ok) setOverview(fresh.data);
    });
  };

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-[28px] font-semibold tracking-[-0.6px] leading-none">
          Facturación
        </h1>
        <p className="text-sm text-muted mt-2">
          Carga el listado simulado de cuotas de los estudiantes · datos de
          prueba, sin integración con el sistema financiero
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MiniStat
          label="Estudiantes"
          value={(overview?.students ?? 0).toLocaleString("es-PE")}
        />
        <MiniStat
          label="Cuotas cargadas"
          value={(overview?.installments ?? 0).toLocaleString("es-PE")}
        />
        <MiniStat
          label="Cuotas pendientes"
          value={(overview?.pending_installments ?? 0).toLocaleString("es-PE")}
        />
        <MiniStat
          label="Total pendiente"
          value={
            overview
              ? fmtMoney(overview.total_pending, overview.currency)
              : "—"
          }
        />
      </div>

      <Card className="p-7 flex flex-col gap-5">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
              Cargar facturación
            </h3>
            <p className="text-sm text-muted mt-1">
              Sube un archivo <span className="font-medium">.xlsx</span> o{" "}
              <span className="font-medium">.csv</span>. Cada fila es una cuota;
              se actualiza por teléfono + ciclo + número.
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={downloadTemplate}>
            <Download size={15} strokeWidth={2} />
            Descargar plantilla
          </Button>
        </div>

        <FileDrop
          files={files}
          onChange={setFiles}
          accept=".xlsx,.csv"
          maxSizeMB={5}
          onError={(msg) =>
            toast.error("Archivo no válido", { description: msg })
          }
        />

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={isPending || files.length === 0}
          >
            {isPending ? "Cargando…" : "Cargar facturación"}
          </Button>
          <span className="text-xs text-muted">
            Columnas: telefono, ciclo, numero, concepto, monto, vencimiento,
            estado, fecha_pago
          </span>
        </div>
      </Card>

      {result ? (
        <Card className="p-7 flex flex-col gap-4">
          <h3 className="text-[18px] font-semibold tracking-[-0.2px]">
            Resultado de la última carga
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <MiniStat label="Estudiantes" value={result.students} />
            <MiniStat label="Nuevas" value={result.inserted} />
            <MiniStat label="Actualizadas" value={result.updated} />
            <MiniStat
              label="Con error"
              value={result.skipped}
              trend={
                result.skipped > 0
                  ? { text: "revisar", direction: "down", tone: "primary" }
                  : undefined
              }
            />
          </div>
          {result.errors.length > 0 ? (
            <div className="flex flex-col gap-1.5">
              <div className="text-[13px] font-medium text-fg-2">
                Filas con problemas
              </div>
              <ul className="flex flex-col gap-1 max-h-56 overflow-y-auto">
                {result.errors.map((e, i) => (
                  <li
                    key={i}
                    className="text-[12px] text-primary bg-primary-soft rounded-lg px-3 py-1.5"
                  >
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-success">
              Todas las filas se cargaron sin errores. ✅
            </p>
          )}
        </Card>
      ) : null}
    </div>
  );
}
