"""Scoped aliases and durable system-event replay protection."""

from sqlalchemy import BigInteger, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk


class WhatsAppIdentity(IdPk, Base):
    __tablename__ = "whatsapp_identities"
    __table_args__ = (UniqueConstraint("scope", "user_id"),)

    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(160), nullable=False)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), index=True
    )
    business_phone_number_id: Mapped[str | None] = mapped_column(String(160))
    parent_user_id: Mapped[str | None] = mapped_column(String(160))
    username: Mapped[str | None] = mapped_column(String(255))


class WhatsAppIdentityEvent(IdPk, Base):
    __tablename__ = "whatsapp_identity_events"
    __table_args__ = (UniqueConstraint("scope", "meta_message_id"),)

    scope: Mapped[str] = mapped_column(String(255), nullable=False)
    meta_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)


class WhatsAppPhoneQuarantine(Base):
    """Persist ambiguous academic phone evidence until verified operator recovery."""

    __tablename__ = "whatsapp_phone_quarantines"

    phone_e164: Mapped[str] = mapped_column(String(32), primary_key=True)
    conflict_timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)
    original_student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
    conflicting_student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="RESTRICT"), nullable=False
    )
