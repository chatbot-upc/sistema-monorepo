from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import StudentBillingInstallment


class StudentBillingRepository:
    async def list_by_phone(
        self, db: AsyncSession, phone_e164: str
    ) -> list[StudentBillingInstallment]:
        """Todas las cuotas del estudiante, ordenadas por fecha de vencimiento."""
        result = await db.execute(
            select(StudentBillingInstallment)
            .where(StudentBillingInstallment.phone_e164 == phone_e164)
            .order_by(StudentBillingInstallment.due_date)
        )
        return list(result.scalars().all())


student_billing_repository = StudentBillingRepository()
