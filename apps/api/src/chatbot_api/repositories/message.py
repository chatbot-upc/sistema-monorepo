from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Message
from chatbot_api.models.enums import MessageRole

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

    async def get_by_meta_id(
        self, db: AsyncSession, meta_message_id: str
    ) -> Message | None:
        result = await db.execute(
            select(Message).where(Message.meta_message_id == meta_message_id)
        )
        return result.scalars().first()

    async def create_inbound(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        content: str,
        meta_message_id: str,
    ) -> Message | None:
        """Insert an incoming WhatsApp message. Returns None if meta_message_id duplicado."""
        existing = await self.get_by_meta_id(db, meta_message_id)
        if existing is not None:
            return None
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.student,
            content=content,
            retrieved_chunks=[],
            meta_message_id=meta_message_id,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def create_bot(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        content: str,
        retrieved_chunks: list[dict[str, object]] | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        latency_ms: int | None = None,
        model_used: str | None = None,
        meta_message_id: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.bot,
            content=content,
            retrieved_chunks=retrieved_chunks or [],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            model_used=model_used,
            meta_message_id=meta_message_id,
        )
        db.add(msg)
        await db.flush()
        return msg


message_repository = MessageRepository(Message)
