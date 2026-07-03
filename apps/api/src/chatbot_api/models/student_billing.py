from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IdPk, Timestamped
from .enums import BillingStatus


class StudentBillingInstallment(IdPk, Timestamped, Base):
    """Cuota de facturación (simulada) de un estudiante, por número de WhatsApp.

    Datos de pago SIMULADOS (EP08), sin integración con el sistema financiero
    real. Se identifica al estudiante por `phone_e164` (mismo criterio que
    `student_profiles`). Una fila por cuota del ciclo; la consulta del bot agrega
    las pendientes y calcula la próxima por vencer (SW-49/SW-50/SW-51).
    """

    __tablename__ = "student_billing_installments"
    __table_args__ = (
        UniqueConstraint(
            "phone_e164",
            "cycle",
            "number",
            name="uq_student_billing_phone_cycle_number",
        ),
    )

    phone_e164: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cycle: Mapped[str] = mapped_column(String(20), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    concept: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PEN")
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[BillingStatus] = mapped_column(
        Enum(BillingStatus, name="billing_status"),
        nullable=False,
        default=BillingStatus.pendiente,
        index=True,
    )
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True)
