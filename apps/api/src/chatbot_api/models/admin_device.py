from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk, Timestamped


class AdminDevice(IdPk, Timestamped, Base):
    __tablename__ = "admin_devices"
    __table_args__ = (UniqueConstraint("fcm_token", name="uq_admin_devices_fcm_token"),)

    admin_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fcm_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="web")
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
