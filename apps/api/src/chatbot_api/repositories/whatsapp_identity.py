"""Identity writes serialize within a short database transaction.

The global advisory lock avoids lock-order cycles across phone and scoped aliases.
It is released by commit/rollback, before classifier, RAG or network work.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import WhatsAppIdentity, WhatsAppPhoneQuarantine


async def lock_identities(db: AsyncSession) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(748212406)"))


async def get_alias(db: AsyncSession, scope: str, user_id: str) -> WhatsAppIdentity | None:
    result = await db.execute(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.scope == scope, WhatsAppIdentity.user_id == user_id
        )
    )

    return result.scalars().first()


async def get_phone_quarantine(db: AsyncSession, phone: str) -> WhatsAppPhoneQuarantine | None:
    result = await db.execute(
        select(WhatsAppPhoneQuarantine)
        .where(WhatsAppPhoneQuarantine.phone_e164 == phone)
        .execution_options(populate_existing=True)
    )
    return result.scalars().first()
