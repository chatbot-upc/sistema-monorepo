"""Siembra facturación (simulada) para los estudiantes piloto (EP08).

Genera cuotas DETERMINISTAS para cada `student_profiles` existente: matrícula +
5 pensiones del ciclo 2026-1. El estado pagado/pendiente varía por estudiante
(patrón `índice % 4`) para cubrir todos los casos del bot: al día, con cuotas
vencidas, y con próxima cuota por vencer. Sin aleatoriedad → reproducible.

One-shot de dev/demo (como seed_student_profiles). Requiere que los perfiles ya
estén sembrados. Idempotente: upsert por (phone_e164, cycle, number).

    uv run python scripts/seed_student_billing.py
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from chatbot_api.core.db import get_session_factory
from chatbot_api.models import StudentBillingInstallment, StudentProfile
from chatbot_api.models.enums import BillingStatus

CYCLE = "2026-1"

# (concepto, monto, vencimiento) — matrícula + 5 pensiones del ciclo.
INSTALLMENTS: list[tuple[str, Decimal, date]] = [
    ("Matrícula 2026-1", Decimal("850.00"), date(2026, 3, 15)),
    ("Cuota 1 - Pensión", Decimal("1850.00"), date(2026, 4, 15)),
    ("Cuota 2 - Pensión", Decimal("1850.00"), date(2026, 5, 15)),
    ("Cuota 3 - Pensión", Decimal("1850.00"), date(2026, 6, 15)),
    ("Cuota 4 - Pensión", Decimal("1850.00"), date(2026, 7, 15)),
    ("Cuota 5 - Pensión", Decimal("1850.00"), date(2026, 8, 15)),
]

# Cuántas de las 6 cuotas están pagadas, según patrón (índice del estudiante % 4).
# 1 → solo matrícula pagada (varias vencidas). 3 → dos pensiones pagadas (1 vencida).
# 5 → todo pagado salvo la última (sin vencidas). 6 → completamente al día.
PAID_BY_PATTERN = {0: 1, 1: 3, 2: 5, 3: 6}


async def _seed() -> None:
    factory = get_session_factory()
    inserted = 0
    updated = 0
    students = 0
    async with factory() as db:
        phones = (
            await db.execute(
                select(StudentProfile.phone_e164).order_by(
                    StudentProfile.phone_e164
                )
            )
        ).scalars().all()

        for i, phone in enumerate(phones):
            students += 1
            paid_count = PAID_BY_PATTERN[i % 4]
            for idx, (concept, amount, due) in enumerate(INSTALLMENTS):
                number = idx + 1
                is_paid = idx < paid_count
                status = BillingStatus.pagado if is_paid else BillingStatus.pendiente
                paid_at = due if is_paid else None

                existing = (
                    await db.execute(
                        select(StudentBillingInstallment).where(
                            StudentBillingInstallment.phone_e164 == phone,
                            StudentBillingInstallment.cycle == CYCLE,
                            StudentBillingInstallment.number == number,
                        )
                    )
                ).scalars().first()

                if existing is None:
                    db.add(
                        StudentBillingInstallment(
                            phone_e164=phone,
                            cycle=CYCLE,
                            number=number,
                            concept=concept,
                            amount=amount,
                            currency="PEN",
                            due_date=due,
                            status=status,
                            paid_at=paid_at,
                        )
                    )
                    inserted += 1
                else:
                    existing.concept = concept
                    existing.amount = amount
                    existing.currency = "PEN"
                    existing.due_date = due
                    existing.status = status
                    existing.paid_at = paid_at
                    updated += 1
        await db.commit()

    print(
        f"Seed facturación: {inserted} insertadas, {updated} actualizadas, "
        f"para {students} estudiantes (ciclo {CYCLE})"
    )


if __name__ == "__main__":
    asyncio.run(_seed())
