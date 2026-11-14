from datetime import datetime

import structlog
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Student, WhatsAppPhoneQuarantine

from .base import BaseRepository


class _StudentCreate(BaseModel):
    pass


class _StudentUpdate(BaseModel):
    pass


class StudentRepository(BaseRepository[Student, _StudentCreate, _StudentUpdate]):
    async def get_by_phone(self, db: AsyncSession, phone_e164: str) -> Student | None:
        result = await db.execute(
            select(Student)
            .where(
                Student.phone_e164 == phone_e164,
                ~Student.phone_e164.in_(select(WhatsAppPhoneQuarantine.phone_e164)),
            )
            .execution_options(populate_existing=True)
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
        from .whatsapp_identity import get_phone_quarantine, lock_identities

        await lock_identities(db)
        if await get_phone_quarantine(db, phone_e164):
            structlog.get_logger().warning(
                "whatsapp_phone_quarantined", source="legacy_phone_upsert"
            )
            raise ValueError("Phone is quarantined; verified operator recovery required")
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
