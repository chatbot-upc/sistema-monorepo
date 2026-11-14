"""Identity writes serialize within a short database transaction.

The global advisory lock avoids lock-order cycles across phone and scoped aliases.
It is released by commit/rollback, before classifier, RAG or network work.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import WhatsAppIdentity


async def lock_identities(db: AsyncSession) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(748212406)"))


async def get_alias(db: AsyncSession, scope: str, user_id: str) -> WhatsAppIdentity | None:
    result = await db.execute(
        select(WhatsAppIdentity).where(
            WhatsAppIdentity.scope == scope, WhatsAppIdentity.user_id == user_id
        )
    )

    return result.scalars().first()
