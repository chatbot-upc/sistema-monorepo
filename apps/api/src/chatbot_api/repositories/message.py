from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Message
from chatbot_api.models.enums import MessageDeliveryStatus, MessageRole

from .base import BaseRepository


class _MsgCreate(BaseModel):
    pass


class _MsgUpdate(BaseModel):
    pass


_DELIVERY_RANK = {"sent": 1, "delivered": 2, "read": 3}


def _should_advance_delivery(current: str | None, new: str) -> bool:
    """Guarda monotónica: nunca retroceder (p. ej. de read a delivered).

    `failed` solo aplica si el mensaje aún no fue entregado/leído.
    """
    if new == "failed":
        return current in (None, "sent")
    if current == "failed":
        return False
    return _DELIVERY_RANK.get(new, 0) > _DELIVERY_RANK.get(current or "", 0)


def build_quoted_snapshot(msg: Message) -> dict[str, object]:
    """Congela el snapshot del mensaje citado para almacenarlo en Message.quoted.

    Inmutable por diseño: los mensajes no se editan, así que el snapshot nunca se
    desincroniza. Si el original se borra (FK SET NULL), el texto citado persiste.
    """
    return {
        "id": msg.id,
        "role": msg.role.value,
        "content": (msg.content or "")[:120],
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


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

    async def list_recent_for_conversation(
        self,
        db: AsyncSession,
        conversation_id: int,
        *,
        since: datetime,
        exclude_after_id: int | None = None,
        limit: int = 20,
    ) -> list[Message]:
        """Last N student/bot messages of a conversation since `since`.

        Used to feed conversation history to the RAG agent (SW-18/SW-25).
        Returned ASC by id so the caller can map directly to chat history.
        `exclude_after_id` filters out the inbound of the current turn (and any
        bot message already inserted in this turn, e.g. the welcome template).
        """
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.created_at >= since,
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
        if exclude_after_id is not None:
            stmt = stmt.where(Message.id < exclude_after_id)
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return rows

    async def list_by_ids(
        self, db: AsyncSession, ids: list[int]
    ) -> list[Message]:
        """Carga mensajes por una lista de ids (orden no garantizado).

        Usado por el debounce para consolidar el lote de mensajes pendientes.
        """
        if not ids:
            return []
        result = await db.execute(select(Message).where(Message.id.in_(ids)))
        return list(result.scalars().all())

    async def get_by_meta_id(
        self, db: AsyncSession, meta_message_id: str
    ) -> Message | None:
        result = await db.execute(
            select(Message).where(Message.meta_message_id == meta_message_id)
        )
        return result.scalars().first()

    async def update_delivery_status(
        self, db: AsyncSession, meta_message_id: str, status: str
    ) -> Message | None:
        """Avanza el acuse de un saliente. Devuelve el Message si cambió, si no None.

        No-op (None) si el mensaje no existe o el estado no avanza (monotónico).
        """
        msg = await self.get_by_meta_id(db, meta_message_id)
        if msg is None or not _should_advance_delivery(msg.delivery_status, status):
            return None
        msg.delivery_status = status
        await db.flush()
        return msg

    async def create_inbound(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        content: str,
        meta_message_id: str,
        in_reply_to_id: int | None = None,
        quoted: dict[str, object] | None = None,
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
            in_reply_to_id=in_reply_to_id,
            quoted=quoted,
        )
        db.add(msg)
        await db.flush()
        return msg

    async def create_admin_message(
        self,
        db: AsyncSession,
        *,
        conversation_id: int,
        content: str,
        admin_id: int,
        meta_message_id: str | None = None,
        in_reply_to_id: int | None = None,
        quoted: dict[str, object] | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.admin,
            content=content,
            admin_id=admin_id,
            meta_message_id=meta_message_id,
            in_reply_to_id=in_reply_to_id,
            quoted=quoted,
            delivery_status=MessageDeliveryStatus.sent.value,
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
        in_reply_to_id: int | None = None,
        quoted: dict[str, object] | None = None,
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
            in_reply_to_id=in_reply_to_id,
            quoted=quoted,
            delivery_status=MessageDeliveryStatus.sent.value,
        )
        db.add(msg)
        await db.flush()
        return msg


message_repository = MessageRepository(Message)
