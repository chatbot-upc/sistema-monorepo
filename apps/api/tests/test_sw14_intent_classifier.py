"""SW-14 + SW-15 — intent classifier (SBERT + LLM fallback) and persistence."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import ConversationIntent, Message
from chatbot_api.repositories.intent import intent_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import intent_classifier_service
from chatbot_api.workers.conversation import _process_async


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_classifier_index() -> None:
    intent_classifier_service.reset_index()
    yield
    intent_classifier_service.reset_index()


# ----- SBERT primary classification (real model) ---------------------------------


@pytest.mark.asyncio
async def test_sbert_classifies_matricula_dates(db_session: AsyncSession) -> None:
    """A textbook 'fechas' query should resolve to consulta_fechas with high confidence."""
    result = await intent_classifier_service.classify(
        db=db_session, text="hasta cuando puedo matricularme este ciclo"
    )
    assert result["sbert_intent_name"] == "consulta_fechas"
    assert result["sbert_confidence"] >= 0.55
    assert result["used_fallback"] is False
    assert result["intent_name"] == "consulta_fechas"


@pytest.mark.asyncio
async def test_sbert_handles_typo_and_colloquial(db_session: AsyncSession) -> None:
    """HU05: errores ortográficos + coloquial should still map to the right intent."""
    result = await intent_classifier_service.classify(
        db=db_session, text="cuanto sale la cuota de matricula?"  # "sale" = cost slang
    )
    assert result["sbert_intent_name"] == "consulta_costos"


# ----- LLM fallback path ----------------------------------------------------------


@pytest.mark.asyncio
async def test_falls_back_to_llm_when_sbert_below_threshold(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If SBERT score < threshold the LLM is invoked and its name is returned."""
    monkeypatch.setattr(
        intent_classifier_service,
        "_sbert_classify",
        lambda text, index: (None, "consulta_fechas", 0.20),
    )
    fake_response = MagicMock()
    fake_response.content = "consulta_becas"
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(intent_classifier_service, "_get_llm", lambda: fake_llm)

    result = await intent_classifier_service.classify(
        db=db_session, text="anything goes here"
    )
    assert result["used_fallback"] is True
    assert result["intent_name"] == "consulta_becas"
    assert result["intent_id"] is not None
    assert result["sbert_confidence"] == 0.20


@pytest.mark.asyncio
async def test_llm_unknown_intent_returns_none(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        intent_classifier_service,
        "_sbert_classify",
        lambda text, index: (None, None, 0.10),
    )
    fake_response = MagicMock()
    fake_response.content = "intent_that_does_not_exist"
    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(intent_classifier_service, "_get_llm", lambda: fake_llm)

    result = await intent_classifier_service.classify(db=db_session, text="x")
    assert result["used_fallback"] is True
    assert result["intent_id"] is None
    assert result["intent_name"] is None


# ----- SW-15 persistence path (worker E2E) ----------------------------------------


def _parsed(meta_id: str, phone: str, text: str) -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Intent Test",
        text=text,
        timestamp="1700000000",
    ).model_dump()


@pytest.mark.asyncio
async def test_worker_persists_intent_id_and_conversation_intent(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SW-15: tras clasificar, messages.intent_id se setea y conversation_intents tiene fila."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900014001"

    # Pre-create student (no welcome path) and discover one real intent_id.
    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        fechas = await intent_repository.get_by_name(setup_db, "consulta_fechas")
        assert fechas is not None
        target_intent_id = fechas.id
        await setup_db.commit()
    await setup_engine.dispose()

    classify_stub = AsyncMock(
        return_value={
            "intent_id": target_intent_id,
            "intent_name": "consulta_fechas",
            "confidence": 0.82,
            "used_fallback": False,
            "sbert_intent_name": "consulta_fechas",
            "sbert_confidence": 0.82,
        }
    )

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            classify_stub,
        ),
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            AsyncMock(return_value={"text": "respuesta", "tool_calls": []}),
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.intent.bot.1"),
        ),
    ):
        await _process_async(
            _parsed("wamid.intent.in.1", phone, "cuando inicia la matricula"),
            "corr-intent",
        )

    verify_engine = create_async_engine(postgres_url)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    async with verify_factory() as verify:
        inbound = (
            await verify.execute(
                select(Message).where(Message.meta_message_id == "wamid.intent.in.1")
            )
        ).scalars().one()
        ci_rows = (
            await verify.execute(
                select(ConversationIntent).where(
                    ConversationIntent.conversation_id == inbound.conversation_id
                )
            )
        ).scalars().all()
    await verify_engine.dispose()

    assert inbound.intent_id == target_intent_id
    assert len(ci_rows) == 1
    assert ci_rows[0].intent_id == target_intent_id
    assert ci_rows[0].confidence == pytest.approx(0.82, rel=1e-3)
