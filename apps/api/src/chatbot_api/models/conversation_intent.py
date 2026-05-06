from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConversationIntent(Base):
    __tablename__ = "conversation_intents"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    intent_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("intents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    detected_at: Mapped[datetime] = mapped_column(
        primary_key=True,
        server_default=func.now(),
    )
    confidence: Mapped[float] = mapped_column(nullable=False)
