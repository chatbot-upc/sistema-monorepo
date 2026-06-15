from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk, Timestamped


class Tag(IdPk, Timestamped, Base):
    """Etiqueta reutilizable del catálogo global.

    Se crea una vez y se asigna a múltiples conversaciones vía
    `conversation_tags`. `color` es una clave de paleta (ver schemas.tag).
    """

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="blue")
