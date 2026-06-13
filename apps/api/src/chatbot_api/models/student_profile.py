from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, Timestamped


class StudentProfile(Timestamped, Base):
    """Perfil académico (simulado) del estudiante, identificado por su número.

    Independiente de `students` (que se crea on-first-contact). Se siembra desde
    un dataset externo y se consulta por `phone_e164` cuando el estudiante escribe
    para personalizar las respuestas del bot (SW-48 y bloque perfil).
    """

    __tablename__ = "student_profiles"

    phone_e164: Mapped[str] = mapped_column(String(32), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    career: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cycle: Mapped[int | None] = mapped_column(Integer, nullable=True)
    campus: Mapped[str | None] = mapped_column(String(80), nullable=True)
    modality: Mapped[str | None] = mapped_column(String(40), nullable=True)
    academic_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    failed_courses: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrollment_turn: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    english_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elective_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internship_credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
