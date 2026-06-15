"""Perfil del estudiante → bloque de contexto para el agente (SW-48).

El worker llama `get_profile_context(db, phone)` antes de invocar al agente. Si
hay perfil, devuelve un bloque de texto legible que se antepone al system prompt
para que el bot personalice (saludo por nombre, turno de matrícula, inglés, etc.).
None si el número no está registrado → el bot opera sin personalización.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.programs import canonical_program
from chatbot_api.models import StudentProfile
from chatbot_api.repositories.student_profile import student_profile_repository

_ENGLISH_MAX = 5

_WEEKDAYS_ES = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]
_MONTHS_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def _fmt_turn(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    weekday = _WEEKDAYS_ES[dt.weekday()]
    month = _MONTHS_ES[dt.month - 1]
    return f"{weekday} {dt.day} de {month}, {dt.hour:02d}:{dt.minute:02d}"


def _fmt_english(level: int | None) -> str | None:
    if level is None:
        return None
    if level >= _ENGLISH_MAX:
        return f"{level}/{_ENGLISH_MAX} (completo, cumple el requisito de egreso)"
    remaining = _ENGLISH_MAX - level
    plural = "niveles" if remaining != 1 else "nivel"
    return (
        f"{level}/{_ENGLISH_MAX} — te {'faltan' if remaining != 1 else 'falta'} "
        f"{remaining} {plural} para el requisito de egreso"
    )


def _build_context(p: StudentProfile) -> str:
    lines: list[str] = ["## Estudiante actual", f"- Nombre: {p.full_name}"]
    if p.career:
        carrera = f"- Carrera: {p.career}"
        if p.cycle is not None:
            carrera += f" · Ciclo {p.cycle}"
        lines.append(carrera)
    if p.campus or p.modality:
        parts = []
        if p.campus:
            parts.append(f"Campus: {p.campus}")
        if p.modality:
            parts.append(f"Modalidad: {p.modality}")
        lines.append("- " + " · ".join(parts))
    if p.academic_status:
        lines.append(f"- Situación académica: {p.academic_status}")
    turn = _fmt_turn(p.enrollment_turn)
    if turn:
        lines.append(f"- Turno de matrícula 2026-1: {turn}")
    english = _fmt_english(p.english_level)
    if english:
        lines.append(f"- Nivel de inglés: {english}")
    credits = []
    if p.elective_credits is not None:
        credits.append(f"electivos: {p.elective_credits}")
    if p.internship_credits is not None:
        credits.append(f"prácticas preprofesionales: {p.internship_credits}")
    if credits:
        lines.append("- Créditos · " + " · ".join(credits))
    if p.failed_courses:
        lines.append(
            f"- Cursos desaprobados el ciclo anterior: {p.failed_courses}"
        )
    return "\n".join(lines)


async def get_profile_context(
    db: AsyncSession, phone_e164: str
) -> str | None:
    profile = await student_profile_repository.get_by_phone(db, phone_e164)
    if profile is None:
        return None
    return _build_context(profile)


async def get_profile_scope(
    db: AsyncSession, phone_e164: str
) -> tuple[str | None, str | None]:
    """(context, program) en una sola consulta — lo que el worker necesita.

    - context: bloque de texto para el system prompt (None si no hay perfil).
    - program: slug canónico de la carrera para scopear el RAG (SW-46); None si
      no hay perfil o la carrera no normaliza → fail-open (búsqueda global).
    """
    profile = await student_profile_repository.get_by_phone(db, phone_e164)
    if profile is None:
        return None, None
    return _build_context(profile), canonical_program(profile.career)
