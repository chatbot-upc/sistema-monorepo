from typing import Any

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk, Timestamped


class Intent(IdPk, Timestamped, Base):
    __tablename__ = "intents"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )
