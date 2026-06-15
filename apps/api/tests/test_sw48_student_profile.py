"""SW-48 (HU39) — perfil académico del estudiante por número + inyección."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from chatbot_api.core.settings import get_settings
from chatbot_api.models import StudentProfile
from chatbot_api.repositories.student_profile import student_profile_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import student_profile_service
from chatbot_api.workers.conversation import _process_async

_PHONE = "+51900480001"


async def _make_profile(db: AsyncSession, **overrides: Any) -> StudentProfile:
    data: dict[str, Any] = {
        "phone_e164": _PHONE,
        "full_name": "Fabiana Nayeli Mallma Villanueva",
        "career": "Ciencias de la Computación",
        "cycle": 9,
        "campus": "Monterrico",
        "modality": "Presencial",
        "academic_status": "Invicto",
        "failed_courses": "Taller de desempeño 1",
        "enrollment_turn": datetime(2026, 3, 25, 16, 0),
        "english_level": 5,
        "elective_credits": 30,
        "internship_credits": 2,
    }
    data.update(overrides)
    profile = StudentProfile(**data)
    db.add(profile)
    await db.flush()
    return profile


async def test_get_by_phone(db_session: AsyncSession) -> None:
    await _make_profile(db_session)
    found = await student_profile_repository.get_by_phone(db_session, _PHONE)
    assert found is not None
    assert found.full_name.startswith("Fabiana")


async def test_get_profile_context_formats(db_session: AsyncSession) -> None:
    await _make_profile(db_session)
    ctx = await student_profile_service.get_profile_context(db_session, _PHONE)
    assert ctx is not None
    assert "## Estudiante actual" in ctx
    assert "Fabiana Nayeli Mallma Villanueva" in ctx
    assert "Ciclo 9" in ctx
    assert "5/5 (completo" in ctx
    assert "Turno de matrícula 2026-1:" in ctx
    assert "Taller de desempeño 1" in ctx


async def test_english_avance_when_incomplete(db_session: AsyncSession) -> None:
    await _make_profile(db_session, english_level=2)
    ctx = await student_profile_service.get_profile_context(db_session, _PHONE)
    assert ctx is not None
    assert "2/5" in ctx
    assert "3 niveles" in ctx


async def test_get_profile_scope_returns_program(
    db_session: AsyncSession,
) -> None:
    """SW-46: get_profile_scope deriva el slug de carrera para scopear el RAG."""
    await _make_profile(db_session, career="Ing. de Sistemas de Información")
    ctx, program = await student_profile_service.get_profile_scope(
        db_session, _PHONE
    )
    assert ctx is not None
    assert program == "sistemas-informacion"


async def test_get_profile_scope_unknown_phone(db_session: AsyncSession) -> None:
    """Sin perfil → (None, None) → fail-open (búsqueda global)."""
    ctx, program = await student_profile_service.get_profile_scope(
        db_session, "+51999999999"
    )
    assert ctx is None
    assert program is None


async def test_unknown_phone_returns_none(db_session: AsyncSession) -> None:
    ctx = await student_profile_service.get_profile_context(
        db_session, "+51999999999"
    )
    assert ctx is None


@pytest.mark.asyncio
async def test_worker_injects_profile_context(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El worker carga el perfil y lo pasa a rag_service.answer."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    # Sembrar perfil + estudiante (evita el welcome de primer contacto).
    from chatbot_api.repositories.student import student_repository

    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(
            setup_db, phone_e164="+51900480500"
        )
        setup_db.add(
            StudentProfile(
                phone_e164="+51900480500",
                full_name="Sebastián Rojas",
                career="Ing. de Sistemas de Información",
                cycle=9,
                english_level=5,
                enrollment_turn=datetime(2026, 3, 24, 8, 20),
            )
        )
        await setup_db.commit()
    await setup_engine.dispose()

    captured: dict[str, Any] = {}

    async def _capturing_answer(
        *,
        user_text: str,
        correlation_id: str,
        history: list[dict[str, str]] | None = None,
        db: object | None = None,
        profile_context: str | None = None,
        program: str | None = None,
    ) -> dict[str, Any]:
        captured["profile_context"] = profile_context
        captured["program"] = program
        return {"text": "Hola Sebastián, ...", "tool_calls": []}

    stub_intent = AsyncMock(
        return_value={
            "intent_id": None,
            "intent_name": None,
            "confidence": 0.0,
            "used_fallback": False,
            "sbert_intent_name": None,
            "sbert_confidence": 0.0,
        }
    )

    parsed = ParsedInboundMessage(
        meta_message_id="wamid.sw48.in",
        from_phone="+51900480500",
        display_name="Sebas",
        text="hola, cuando es mi turno?",
        timestamp="1700000000",
    ).model_dump()

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            side_effect=_capturing_answer,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.sw48.bot"),
        ),
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            stub_intent,
        ),
    ):
        await _process_async(parsed, "corr-sw48")

    assert captured["profile_context"] is not None
    assert "Sebastián Rojas" in captured["profile_context"]
    # SW-46: el worker deriva el slug de carrera y lo pasa para scopear el RAG.
    assert captured["program"] == "sistemas-informacion"
