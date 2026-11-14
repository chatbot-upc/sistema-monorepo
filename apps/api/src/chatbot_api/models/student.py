from datetime import datetime

from sqlalchemy import BigInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    phone_e164: Mapped[str | None] = mapped_column(String(32), unique=True)
    whatsapp_user_id: Mapped[str | None] = mapped_column(String(160))
    whatsapp_username: Mapped[str | None] = mapped_column(String(255))
    whatsapp_scope: Mapped[str | None] = mapped_column(String(255))
    business_phone_number_id: Mapped[str | None] = mapped_column(String(160))
    whatsapp_routing_id: Mapped[str | None] = mapped_column(String(160))
    identity_timestamp: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )
