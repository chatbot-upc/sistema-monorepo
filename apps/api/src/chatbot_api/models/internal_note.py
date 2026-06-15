from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IdPk, Timestamped

if TYPE_CHECKING:
    from .admin import Admin


class InternalNote(IdPk, Timestamped, Base):
    """Nota interna del asesor sobre una conversación (no visible al estudiante)."""

    __tablename__ = "internal_notes"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped["Admin | None"] = relationship(lazy="selectin")
