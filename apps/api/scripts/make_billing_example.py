"""Genera un Excel de EJEMPLO para la carga de facturación (SW-52).

Escribe `data-facturacion-ejemplo.xlsx` en la raíz del repo con el formato que
espera el endpoint POST /api/v1/billing/import: una fila por cuota, encabezados
en español. Sirve de plantilla para el admin y de archivo de prueba.

    uv run python scripts/make_billing_example.py
"""

from datetime import date
from pathlib import Path

from openpyxl import Workbook

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
OUT_PATH = REPO_ROOT / "data-facturacion-ejemplo.xlsx"

HEADERS = [
    "telefono",
    "ciclo",
    "numero",
    "concepto",
    "monto",
    "vencimiento",
    "estado",
    "fecha_pago",
]

# (concepto, monto, vencimiento)
PLAN = [
    ("Matrícula 2026-1", 850.00, date(2026, 3, 15)),
    ("Cuota 1 - Pensión", 1850.00, date(2026, 4, 15)),
    ("Cuota 2 - Pensión", 1850.00, date(2026, 5, 15)),
    ("Cuota 3 - Pensión", 1850.00, date(2026, 6, 15)),
    ("Cuota 4 - Pensión", 1850.00, date(2026, 7, 15)),
    ("Cuota 5 - Pensión", 1850.00, date(2026, 8, 15)),
]

# (telefono, cuántas cuotas pagadas) — 3 escenarios distintos para probar el bot.
STUDENTS = [
    ("+51911111111", 1),  # solo matrícula pagada → varias vencidas
    ("+51922222222", 3),  # dos pensiones pagadas → 1 vencida
    ("+51933333333", 6),  # todo pagado → al día
]


def main() -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Facturacion"
    ws.append(HEADERS)

    for phone, paid_count in STUDENTS:
        for idx, (concept, amount, due) in enumerate(PLAN):
            number = idx + 1
            is_paid = idx < paid_count
            ws.append(
                [
                    phone,
                    "2026-1",
                    number,
                    concept,
                    amount,
                    due.isoformat(),
                    "pagado" if is_paid else "pendiente",
                    due.isoformat() if is_paid else "",
                ]
            )

    wb.save(OUT_PATH)
    print(f"Escrito {OUT_PATH} ({len(STUDENTS)} estudiantes x {len(PLAN)} cuotas)")


if __name__ == "__main__":
    main()
