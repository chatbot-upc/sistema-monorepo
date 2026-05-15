from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    ) -> Student:
        """Insert student if missing; bump last_seen_at and keep display_name if not provided."""
        base = pg_insert(Student).values(
            phone_e164=phone_e164, display_name=display_name
        )
        stmt = base.on_conflict_do_update(
            index_elements=[Student.phone_e164],
            set_={
                "last_seen_at": func.now(),
                "display_name": func.coalesce(
                    base.excluded.display_name, Student.display_name
                ),
            },
        )
        await db.execute(stmt)
        student = await self.get_by_phone(db, phone_e164)
        assert student is not None
        return student

    async def touch_last_seen(self, db: AsyncSession, phone_e164: str) -> None:
        await db.execute(
            update(Student)
            .where(Student.phone_e164 == phone_e164)
            .values(last_seen_at=datetime.now())
        )


student_repository = StudentRepository(Student)
