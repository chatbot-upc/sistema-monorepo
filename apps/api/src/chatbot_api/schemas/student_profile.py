from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentProfileRead(BaseModel):
    """Perfil académico del estudiante (sembrado desde dataset externo).

    Se expone en el detalle de conversación para mostrar en el CRM la info
    del alumno asociado al número (carrera, ciclo, etc.).
    """

    model_config = ConfigDict(from_attributes=True)

    phone_e164: str
    full_name: str
    career: str | None
    cycle: int | None
    campus: str | None
    modality: str | None
    academic_status: str | None
    failed_courses: str | None
    enrollment_turn: datetime | None
    english_level: int | None
    elective_credits: int | None
    internship_credits: int | None
