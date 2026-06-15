from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ConversationTag(Base):
    """Tabla puente entre conversaciones y etiquetas (N:N)."""

    __tablename__ = "conversation_tags"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
