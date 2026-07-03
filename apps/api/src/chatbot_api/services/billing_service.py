"""Consulta de facturación simulada del estudiante (EP08).

Datos de pago SIMULADOS, sin integración con el sistema financiero real. El
worker llama `build_payment_reply(db, phone_e164=...)` cuando el clasificador
resuelve la intención a `consulta_pagos`; devuelve un mensaje determinista
(montos y fechas exactos, sin pasar por el LLM) que cubre HU41 (pagos pendientes)
y HU42 (monto adeudado y fecha de vencimiento de la próxima cuota).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import StudentBillingInstallment
from chatbot_api.models.enums import BillingStatus
from chatbot_api.repositories.student_billing import student_billing_repository

# America/Lima es UTC-5 todo el año (sin DST); mismo criterio que core.timezone.
_LOCAL_UTC_OFFSET = timedelta(hours=-5)

_MONTHS_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]

_NO_DATA_REPLY = (
    "No encontré información de pagos asociada a tu número. 🤔\n\n"
    "Es posible que tu matrícula aún no esté registrada. Si crees que es un "
    "error, escríbenos y con gusto te derivamos con un asesor."
)

_DISCLAIMER = (
    "_Información referencial. Si necesitas ayuda con tu pago, escríbenos y te "
    "derivamos con un asesor._"
)


def _today_local() -> date:
    return (datetime.now(UTC) + _LOCAL_UTC_OFFSET).date()


def _fmt_money(amount: Decimal, currency: str = "PEN") -> str:
    prefix = "S/ " if currency == "PEN" else f"{currency} "
    return f"{prefix}{amount:,.2f}"


def _fmt_date(d: date) -> str:
    return f"{d.day} de {_MONTHS_ES[d.month - 1]} de {d.year}"


@dataclass
class BillingSummary:
    cycle: str | None
    pending: list[StudentBillingInstallment]
    total_pending: Decimal
    next_installment: StudentBillingInstallment | None
    overdue: list[StudentBillingInstallment]
    all_paid: bool


async def get_summary(
    db: AsyncSession, *, phone_e164: str
) -> BillingSummary | None:
    """Agrega la facturación del estudiante. None si no tiene registros."""
    rows = await student_billing_repository.list_by_phone(db, phone_e164)
    if not rows:
        return None
    today = _today_local()
    pending = [r for r in rows if r.status == BillingStatus.pendiente]
    overdue = [r for r in pending if r.due_date < today]
    total_pending = sum((r.amount for r in pending), Decimal("0"))
    next_installment = min(pending, key=lambda r: r.due_date) if pending else None
    cycle = next_installment.cycle if next_installment else rows[-1].cycle
    return BillingSummary(
        cycle=cycle,
        pending=pending,
        total_pending=total_pending,
        next_installment=next_installment,
        overdue=overdue,
        all_paid=not pending,
    )


def render_reply(summary: BillingSummary) -> str:
    """Mensaje determinista de WhatsApp con el estado de pagos del estudiante."""
    cycle_suffix = f" · Ciclo {summary.cycle}" if summary.cycle else ""

    if summary.all_paid:
        return (
            f"✅ ¡Estás al día! No tienes cuotas pendientes de pago{cycle_suffix}.\n\n"
            f"{_DISCLAIMER}"
        )

    lines: list[str] = [f"💳 *Estado de tus pagos*{cycle_suffix}", ""]

    n = len(summary.pending)
    plural = "cuota pendiente" if n == 1 else "cuotas pendientes"
    lines.append(
        f"Tienes *{n} {plural}* por un total de "
        f"*{_fmt_money(summary.total_pending)}*."
    )

    if summary.next_installment is not None:
        ni = summary.next_installment
        lines += [
            "",
            f"📅 Próxima cuota: *{ni.concept}* — {_fmt_money(ni.amount, ni.currency)}, "
            f"vence el *{_fmt_date(ni.due_date)}*.",
        ]

    if summary.overdue:
        ov = len(summary.overdue)
        vencidas = "vencida" if ov == 1 else "vencidas"
        esta = "está" if ov == 1 else "están"
        lines += [
            "",
            f"⚠️ {ov} de tus cuotas ya {esta} {vencidas}. Regulariza tu pago "
            "para evitar recargos.",
        ]

    today = _today_local()
    lines += ["", "Detalle de cuotas pendientes:"]
    for r in summary.pending:
        mark = "🔴" if r.due_date < today else "•"
        lines.append(
            f"{mark} {r.concept}: {_fmt_money(r.amount, r.currency)} — "
            f"vence {_fmt_date(r.due_date)}"
        )

    lines += ["", _DISCLAIMER]
    return "\n".join(lines)


async def build_payment_reply(db: AsyncSession, *, phone_e164: str) -> str:
    """Texto de respuesta a una consulta de pagos. Nunca lanza; siempre devuelve
    un mensaje presentable (mensaje canned si el estudiante no tiene registros)."""
    summary = await get_summary(db, phone_e164=phone_e164)
    if summary is None:
        return _NO_DATA_REPLY
    return render_reply(summary)
