from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Message

from .base import BaseRepository


class _MsgCreate(BaseModel):
    pass


class _MsgUpdate(BaseModel):
    pass


class MessageRepository(BaseRepository[Message, _MsgCreate, _MsgUpdate]):
    async def list_by_conversation(
        self,
        db: AsyncSession,
        conversation_id: int,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Message]:
        result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_conversation(self, db: AsyncSession, conversation_id: int) -> int:
        result = await db.execute(
            select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
        )
        return int(result.scalar_one())


message_repository = MessageRepository(Message)
