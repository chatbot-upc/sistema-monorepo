import type { ReportsData } from "../_actions/reports";

const KPI_ROWS = (d: ReportsData): [string, string][] => [
  ["Total conversaciones", String(d.summary.total)],
  ["Resueltas por bot", String(d.summary.resolved_by_bot)],
  ["Escaladas", String(d.summary.escalated)],
  ["Tasa fallback (%)", String(d.summary.fallback_rate)],
];

function triggerDownload(filename: string, mime: string, content: string) {
  const blob = new Blob([content], { type: `${mime};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function csvCell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
}

function csvRow(cells: string[]): string {
  return cells.map(csvCell).join(",");
}

/** CSV real con las 3 secciones (KPIs, por día, intenciones). */
export function exportCsv(data: ReportsData, range: string, filename: string) {
  const lines: string[] = [];
  lines.push(csvRow(["Reporte UPCBot", range]));
  lines.push("");
  lines.push(csvRow(["KPI", "Valor"]));
  for (const [k, v] of KPI_ROWS(data)) lines.push(csvRow([k, v]));
  lines.push("");
  lines.push(csvRow(["Fecha", "Conversaciones"]));
  for (const p of data.daily) lines.push(csvRow([p.date, String(p.count)]));
  lines.push("");
  lines.push(csvRow(["Intención", "Conteo", "Porcentaje"]));
  for (const i of data.intents)
    lines.push(csvRow([i.intent_name, String(i.count), `${i.percentage}%`]));

  triggerDownload(filename, "text/csv", lines.join("\r\n"));
}

function htmlTable(headers: string[], rows: string[][]): string {
  const head = headers.map((h) => `<th>${h}</th>`).join("");
  const body = rows
    .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`)
    .join("");
  return `<table border="1"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

/** Excel real (.xls vía HTML; Excel/Sheets lo abren directo). */
export function exportExcel(data: ReportsData, range: string, filename: string) {
  const html = `<html><head><meta charset="utf-8" /></head><body>
    <h2>Reporte UPCBot</h2><p>${range}</p>
    <h3>KPIs</h3>${htmlTable(["KPI", "Valor"], KPI_ROWS(data))}
    <h3>Conversaciones por día</h3>${htmlTable(
      ["Fecha", "Conversaciones"],
      data.daily.map((p) => [p.date, String(p.count)]),
    )}
    <h3>Intenciones</h3>${htmlTable(
      ["Intención", "Conteo", "Porcentaje"],
      data.intents.map((i) => [i.intent_name, String(i.count), `${i.percentage}%`]),
    )}
  </body></html>`;
  triggerDownload(filename, "application/vnd.ms-excel", html);
}

/** PDF real vía diálogo de impresión del navegador (Guardar como PDF). */
export function exportPdf(data: ReportsData, range: string) {
  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  win.document.write(`<html><head><meta charset="utf-8" /><title>Reporte UPCBot</title>
    <style>
      body { font-family: system-ui, sans-serif; padding: 32px; color: #0f172a; }
      h1 { font-size: 22px; margin: 0; }
      .sub { color: #64748b; margin: 4px 0 24px; }
      h3 { margin: 24px 0 8px; font-size: 14px; }
      .kpis { display: flex; gap: 16px; flex-wrap: wrap; }
      .kpi { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 18px; min-width: 150px; }
      .kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #64748b; }
      .kpi .val { font-size: 26px; font-weight: 700; margin-top: 4px; }
      table { border-collapse: collapse; width: 100%; font-size: 13px; }
      th, td { border: 1px solid #e2e8f0; padding: 6px 10px; text-align: left; }
      th { background: #f1f5f9; }
    </style></head><body>
    <h1>Reporte UPCBot</h1><div class="sub">${range}</div>
    <div class="kpis">
      ${KPI_ROWS(data)
        .map(
          ([k, v]) =>
            `<div class="kpi"><div class="label">${k}</div><div class="val">${v}</div></div>`,
        )
        .join("")}
    </div>
    <h3>Conversaciones por día</h3>${htmlTable(
      ["Fecha", "Conversaciones"],
      data.daily.map((p) => [p.date, String(p.count)]),
    )}
    <h3>Intenciones más frecuentes</h3>${htmlTable(
      ["Intención", "Conteo", "Porcentaje"],
      data.intents.map((i) => [i.intent_name, String(i.count), `${i.percentage}%`]),
    )}
  </body></html>`);
  win.document.close();
  win.focus();
  win.print();
}
