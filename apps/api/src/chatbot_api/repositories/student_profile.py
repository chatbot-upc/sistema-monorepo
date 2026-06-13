from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import StudentProfile


class StudentProfileRepository:
    async def get_by_phone(
        self, db: AsyncSession, phone_e164: str
    ) -> StudentProfile | None:
        result = await db.execute(
            select(StudentProfile).where(
                StudentProfile.phone_e164 == phone_e164
            )
        )
        return result.scalars().first()


student_profile_repository = StudentProfileRepository()
