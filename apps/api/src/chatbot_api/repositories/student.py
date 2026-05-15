from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Student

from .base import BaseRepository


class _StudentCreate(BaseModel):
    pass


class _StudentUpdate(BaseModel):
    pass


class StudentRepository(BaseRepository[Student, _StudentCreate, _StudentUpdate]):
    async def get_by_phone(self, db: AsyncSession, phone_e164: str) -> Student | None:
        result = await db.execute(
            select(Student).where(Student.phone_e164 == phone_e164)
        )
        return result.scalars().first()

    async def upsert_by_phone(
        self,
        db: AsyncSession,
        *,
        phone_e164: str,
        display_name: str | None = None,
    ) -> tuple[Student, bool]:
        """Get or create. Returns (student, created).

        On existing rows: bump last_seen_at and refresh display_name if a new one came.
        Two queries beat the pg_insert RETURNING dance for read clarity at this scale.
        """
        existing = await self.get_by_phone(db, phone_e164)
        if existing is None:
            student = Student(phone_e164=phone_e164, display_name=display_name)
            db.add(student)
            await db.flush()
            return student, True
        existing.last_seen_at = datetime.now()
        if display_name and not existing.display_name:
            existing.display_name = display_name
        await db.flush()
        return existing, False

    async def touch_last_seen(self, db: AsyncSession, phone_e164: str) -> None:
        await db.execute(
            update(Student)
            .where(Student.phone_e164 == phone_e164)
            .values(last_seen_at=datetime.now())
        )


student_repository = StudentRepository(Student)
