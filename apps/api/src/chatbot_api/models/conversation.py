from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdPk, Timestamped
from .enums import ConversationStatus

if TYPE_CHECKING:
    from .message import Message
    from .student import Student
    from .tag import Tag


class Conversation(IdPk, Timestamped, Base):
    __tablename__ = "conversations"

    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    student_phone: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, name="conversation_status"),
        nullable=False,
        default=ConversationStatus.abierta,
        index=True,
    )
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    takeover_admin: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    starred: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Última vez que un admin abrió el hilo en el CRM (compartido entre admins,
    # como Chatwoot). Los mensajes del estudiante posteriores cuentan como no
    # leídos. NULL = nunca abierto → todo lo entrante está sin leer.
    agent_last_seen_at: Mapped[datetime | None] = mapped_column(nullable=True)

    student: Mapped["Student"] = relationship(lazy="selectin")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="conversation_tags",
        lazy="selectin",
        order_by="Tag.name",
    )
