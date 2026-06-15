"""SW-46 — normalización canónica de carrera (sin DB, sin OpenAI)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.programs import canonical_program


@pytest.mark.parametrize(
    ("career", "title"),
    [
        (
            "Ing. de Sistemas de Información",
            "INGENIERIA DE SISTEMAS DE INFORMACION PREGRADO MW FDM",
        ),
        ("Ciencias de la Computación", "CIENCIAS DE LA COMPUTACION PREGRADO FDM PRESENCIAL"),
        ("Ing. de Software", "INGENIERIA-DE-SOFTWARE-PREGRADO-MW-FDM"),
        ("Derecho", "DERECHO PREGRADO FDM"),
        ("Ing. Civil", "INGENIERIA CIVIL PREGRADO MW FDM"),
    ],
)
def test_career_and_title_converge(career: str, title: str) -> None:
    """La carrera del alumno y el título de la malla caen al MISMO slug."""
    a = canonical_program(career)
    b = canonical_program(title)
    assert a is not None
    assert a == b


def test_distinct_careers_distinct_slugs() -> None:
    """Carreras parecidas NO colisionan (lo que causaba el bug original)."""
    si = canonical_program("Ing. de Sistemas de Información")
    cc = canonical_program("Ciencias de la Computación")
    sw = canonical_program("Ing. de Software")
    assert len({si, cc, sw}) == 3


@pytest.mark.parametrize("text", ["", "   ", None, "Ing. de", "PREGRADO MW FDM"])
def test_empty_or_only_filler_returns_none(text: str | None) -> None:
    """Texto vacío o solo relleno → None (→ fail-open en el retrieval)."""
    assert canonical_program(text) is None


def test_slug_is_lowercase_hyphenated() -> None:
    assert canonical_program("Ing. de Sistemas de Información") == "sistemas-informacion"


async def test_list_program_options_dedupes_by_slug(
    db_session: AsyncSession,
) -> None:
    """Las opciones del selector salen de las carreras de los alumnos, sin dups."""
    from chatbot_api.models import StudentProfile
    from chatbot_api.services import document_service

    db_session.add_all(
        [
            StudentProfile(
                phone_e164="+51900000001",
                full_name="A",
                career="Ing. de Sistemas de Información",
            ),
            StudentProfile(
                phone_e164="+51900000002",
                full_name="B",
                career="Ing. de Sistemas de Información",  # mismo slug
            ),
            StudentProfile(
                phone_e164="+51900000003",
                full_name="C",
                career="Derecho",
            ),
        ]
    )
    await db_session.flush()

    options = await document_service.list_program_options(db_session)
    values = {o.value for o in options}
    assert "sistemas-informacion" in values
    assert "derecho" in values
    # dedupe: dos alumnos de SI → una sola opción
    assert len([o for o in options if o.value == "sistemas-informacion"]) == 1
