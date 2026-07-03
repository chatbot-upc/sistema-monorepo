"""Carga de facturación simulada desde archivo (EP08 / SW-52).

El admin sube un Excel (.xlsx) o CSV con las cuotas de los estudiantes desde la
web; este módulo lo parsea y hace upsert por (phone_e164, cycle, number).
Complementa al seed por script: en el piloto el admin gestiona los datos sin
tocar el servidor. Aislado de `billing_service` (respuesta del bot) para no
cargar openpyxl en el proceso del worker.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import StudentBillingInstallment
from chatbot_api.models.enums import BillingStatus
from chatbot_api.schemas.billing import BillingImportResult, BillingOverview

# Encabezado (normalizado a minúsculas) → campo canónico. Tolera español/inglés.
_HEADER_ALIASES: dict[str, str] = {
    "telefono": "phone",
    "teléfono": "phone",
    "celular": "phone",
    "whatsapp": "phone",
    "phone": "phone",
    "phone_e164": "phone",
    "ciclo": "cycle",
    "cycle": "cycle",
    "numero": "number",
    "número": "number",
    "nro": "number",
    "numero_cuota": "number",
    "number": "number",
    "concepto": "concept",
    "descripcion": "concept",
    "descripción": "concept",
    "concept": "concept",
    "monto": "amount",
    "importe": "amount",
    "amount": "amount",
    "vencimiento": "due_date",
    "vence": "due_date",
    "fecha_vencimiento": "due_date",
    "due_date": "due_date",
    "estado": "status",
    "status": "status",
    "fecha_pago": "paid_at",
    "pagado_el": "paid_at",
    "paid_at": "paid_at",
    "moneda": "currency",
    "currency": "currency",
}

_REQUIRED = ["phone", "cycle", "number", "concept", "amount", "due_date"]

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d")


@dataclass
class _Row:
    phone_e164: str
    cycle: str
    number: int
    concept: str
    amount: Decimal
    currency: str
    due_date: date
    status: BillingStatus
    paid_at: date | None


def _norm_phone(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(" ", "")
    if not s:
        return None
    return s if s.startswith("+") else f"+{s}"


def _to_int(raw: Any) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(float(str(raw).strip()))
    except (ValueError, TypeError):
        return None


def _to_decimal(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    # Quita espacios y separadores de miles (coma); deja el punto decimal.
    s = str(raw).strip().replace(" ", "").replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def _to_date(raw: Any) -> date | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _to_str(raw: Any) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    return s or None


def _to_status(raw: Any) -> BillingStatus:
    s = str(raw or "").strip().lower()
    if s in ("pagado", "pagada", "paid", "cancelado", "cancelada"):
        return BillingStatus.pagado
    return BillingStatus.pendiente


def _read_raw_rows(filename: str | None, content: bytes) -> list[list[Any]]:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = content.decode("utf-8-sig", errors="replace")
        return [list(r) for r in csv.reader(io.StringIO(text))]
    if name.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
        ws = wb.active
        if ws is None:
            return []
        return [list(r) for r in ws.iter_rows(values_only=True)]
    raise ValueError("Formato no soportado. Sube un archivo .xlsx o .csv.")


def parse(filename: str | None, content: bytes) -> tuple[list[_Row], list[str]]:
    """Parsea el archivo → (filas válidas, errores por fila). Nunca lanza salvo
    formato no soportado (ValueError)."""
    raw_rows = _read_raw_rows(filename, content)
    if not raw_rows:
        return [], ["El archivo está vacío."]

    header = [
        str(c).strip().lower() if c is not None else "" for c in raw_rows[0]
    ]
    col: dict[str, int] = {}
    for idx, h in enumerate(header):
        field = _HEADER_ALIASES.get(h)
        if field and field not in col:
            col[field] = idx

    missing = [f for f in _REQUIRED if f not in col]
    if missing:
        return [], [
            "Faltan columnas obligatorias: "
            + ", ".join(missing)
            + ". Descarga la plantilla para ver el formato esperado."
        ]

    def cell(row: list[Any], field: str) -> Any:
        i = col.get(field)
        return row[i] if i is not None and i < len(row) else None

    rows: list[_Row] = []
    errors: list[str] = []
    for n, r in enumerate(raw_rows[1:], start=2):
        if not r or all(c is None or str(c).strip() == "" for c in r):
            continue  # fila en blanco

        phone = _norm_phone(cell(r, "phone"))
        cycle = _to_str(cell(r, "cycle"))
        number = _to_int(cell(r, "number"))
        concept = _to_str(cell(r, "concept"))
        amount = _to_decimal(cell(r, "amount"))
        due = _to_date(cell(r, "due_date"))

        problems: list[str] = []
        if not phone:
            problems.append("teléfono inválido")
        if not cycle:
            problems.append("ciclo vacío")
        if number is None:
            problems.append("número inválido")
        if not concept:
            problems.append("concepto vacío")
        if amount is None or amount < 0:
            problems.append("monto inválido")
        if due is None:
            problems.append("vencimiento inválido")
        if problems:
            errors.append(f"Fila {n}: {', '.join(problems)}.")
            continue

        assert phone is not None and cycle is not None and concept is not None
        assert number is not None and amount is not None and due is not None
        currency = _to_str(cell(r, "currency"))
        rows.append(
            _Row(
                phone_e164=phone,
                cycle=cycle,
                number=number,
                concept=concept,
                amount=amount,
                currency=(currency.upper()[:3] if currency else "PEN"),
                due_date=due,
                status=_to_status(cell(r, "status")),
                paid_at=_to_date(cell(r, "paid_at")),
            )
        )
    return rows, errors


async def import_billing_file(
    db: AsyncSession, *, filename: str | None, content: bytes
) -> BillingImportResult:
    """Parsea y hace upsert de las cuotas. Idempotente por (phone, cycle, number)."""
    try:
        rows, errors = parse(filename, content)
    except ValueError as exc:
        return BillingImportResult(
            students=0, inserted=0, updated=0, skipped=0, errors=[str(exc)]
        )

    inserted = 0
    updated = 0
    phones: set[str] = set()
    for row in rows:
        phones.add(row.phone_e164)
        existing = (
            await db.execute(
                select(StudentBillingInstallment).where(
                    StudentBillingInstallment.phone_e164 == row.phone_e164,
                    StudentBillingInstallment.cycle == row.cycle,
                    StudentBillingInstallment.number == row.number,
                )
            )
        ).scalars().first()
        if existing is None:
            db.add(
                StudentBillingInstallment(
                    phone_e164=row.phone_e164,
                    cycle=row.cycle,
                    number=row.number,
                    concept=row.concept,
                    amount=row.amount,
                    currency=row.currency,
                    due_date=row.due_date,
                    status=row.status,
                    paid_at=row.paid_at,
                )
            )
            inserted += 1
        else:
            existing.concept = row.concept
            existing.amount = row.amount
            existing.currency = row.currency
            existing.due_date = row.due_date
            existing.status = row.status
            existing.paid_at = row.paid_at
            updated += 1
    await db.commit()

    return BillingImportResult(
        students=len(phones),
        inserted=inserted,
        updated=updated,
        skipped=len(errors),
        errors=errors[:50],  # cap para no devolver respuestas gigantes
    )


async def get_overview(db: AsyncSession) -> BillingOverview:
    """Estado actual de la facturación cargada (para el panel admin)."""
    students = (
        await db.execute(
            select(func.count(func.distinct(StudentBillingInstallment.phone_e164)))
        )
    ).scalar_one()
    installments = (
        await db.execute(select(func.count(StudentBillingInstallment.id)))
    ).scalar_one()
    pending = (
        await db.execute(
            select(func.count(StudentBillingInstallment.id)).where(
                StudentBillingInstallment.status == BillingStatus.pendiente
            )
        )
    ).scalar_one()
    total_pending = (
        await db.execute(
            select(
                func.coalesce(func.sum(StudentBillingInstallment.amount), 0)
            ).where(StudentBillingInstallment.status == BillingStatus.pendiente)
        )
    ).scalar_one()

    return BillingOverview(
        students=int(students),
        installments=int(installments),
        pending_installments=int(pending),
        total_pending=Decimal(total_pending),
        currency="PEN",
    )
