"""SW-30 HU21 — detect agent escalate_to_human and flip conversation to takeover."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation
from chatbot_api.models.enums import ConversationStatus
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.workers.conversation import _process_async


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _stub_intent_classifier(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = AsyncMock(
        return_value={
            "intent_id": None,
            "intent_name": None,
            "confidence": 0.0,
            "used_fallback": False,
            "sbert_intent_name": None,
            "sbert_confidence": 0.0,
        }
    )
    monkeypatch.setattr(
        "chatbot_api.workers.conversation.intent_classifier_service.classify", stub
    )


def _parsed(meta_id: str, phone: str, text: str = "no se que mas decir") -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Escalation Test",
        text=text,
        timestamp="1700000000",
    ).model_dump()


async def _seed_student(postgres_url: str, phone: str) -> None:
    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        await setup_db.commit()
    await setup_engine.dispose()


async def _read_conversation(
    postgres_url: str, phone: str
) -> Conversation:
    verify_engine = create_async_engine(postgres_url)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    async with verify_factory() as verify:
        conv = (
            (
                await verify.execute(
                    select(Conversation).where(Conversation.student_phone == phone)
                )
            )
            .scalars()
            .one()
        )
    await verify_engine.dispose()
    return conv


@pytest.mark.asyncio
async def test_escalate_tool_flips_conversation_to_takeover(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900030001"
    await _seed_student(postgres_url, phone)

    fake_answer = AsyncMock(
        return_value={
            "text": "Te derivo con un asesor.",
            "tool_calls": [
                {"name": "search_knowledge_base", "args": {"query": "x"}},
                {
                    "name": "escalate_to_human",
                    "args": {"reason": "no encontré info sobre ese tema"},
                },
            ],
            "input_tokens": 10,
            "output_tokens": 5,
        }
    )

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_answer
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.esc.bot.1"),
        ),
    ):
        await _process_async(
            _parsed("wamid.esc.in.1", phone), "corr-esc"
        )

    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.takeover
    assert conv.meta["escalation_reason"] == "no encontré info sobre ese tema"
    assert "escalated_at" in conv.meta
    assert isinstance(conv.meta["escalated_from_message_id"], int)


@pytest.mark.asyncio
async def test_normal_answer_does_not_escalate(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900030002"
    await _seed_student(postgres_url, phone)

    fake_answer = AsyncMock(
        return_value={
            "text": "Respuesta normal con info.",
            "tool_calls": [
                {"name": "search_knowledge_base", "args": {"query": "matricula"}},
            ],
            "input_tokens": 10,
            "output_tokens": 5,
        }
    )

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_answer
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.noesc.bot.1"),
        ),
    ):
        await _process_async(
            _parsed("wamid.noesc.in.1", phone), "corr-noesc"
        )

    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.abierta
    assert "escalation_reason" not in (conv.meta or {})


@pytest.mark.asyncio
async def test_sbert_solicita_humano_escalates_before_rag(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the intent classifier picks 'solicita_humano', skip RAG entirely
    and flip the conversation to takeover (deterministic path)."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900030010"
    await _seed_student(postgres_url, phone)

    # Look up the real intent_id seeded in migrations (FK to intents.id).
    from chatbot_api.repositories.intent import intent_repository

    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        intent = await intent_repository.get_by_name(setup_db, "solicita_humano")
        assert intent is not None
        solicita_humano_id = intent.id
    await setup_engine.dispose()

    sbert_classify = AsyncMock(
        return_value={
            "intent_id": solicita_humano_id,
            "intent_name": "solicita_humano",
            "confidence": 0.82,
            "used_fallback": False,
            "sbert_intent_name": "solicita_humano",
            "sbert_confidence": 0.82,
        }
    )

    fake_rag = AsyncMock(return_value={"text": "should not run", "tool_calls": []})
    fake_send = AsyncMock(return_value="wamid.sbert.notice")
    fake_push = AsyncMock(return_value=0)

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            sbert_classify,
        ),
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_rag
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            fake_send,
        ),
        patch(
            "chatbot_api.workers.conversation.push_service.notify_all_admins",
            fake_push,
        ),
    ):
        await _process_async(
            _parsed(
                "wamid.sbert.esc.1",
                phone,
                text="quiero hablar con un asesor por favor",
            ),
            "corr-sbert-esc",
        )

    fake_rag.assert_not_awaited()
    # SW-29: student gets the canned notice in the SBERT path.
    fake_send.assert_awaited_once()
    assert fake_send.await_args.kwargs["to"] == phone
    assert "asesor humano" in fake_send.await_args.kwargs["body"].lower()
    # SW-31: push fires too.
    fake_push.assert_awaited_once()

    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.takeover
    assert conv.meta["escalation_source"] == "intent_classifier"
    assert conv.meta["escalation_reason"] == "intent:solicita_humano"


@pytest.mark.asyncio
async def test_llm_escalation_records_source_llm(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM-driven escalation must label source='llm' (vs the SBERT path)."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900030011"
    await _seed_student(postgres_url, phone)

    fake_answer = AsyncMock(
        return_value={
            "text": "Te derivo.",
            "tool_calls": [
                {"name": "escalate_to_human", "args": {"reason": "fuera de scope"}},
            ],
        }
    )

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_answer
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.llm.bot.1"),
        ),
    ):
        await _process_async(
            _parsed("wamid.llm.esc.1", phone, text="alguna pregunta rara"),
            "corr-llm-esc",
        )

    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.takeover
    assert conv.meta["escalation_source"] == "llm"
    assert conv.meta["escalation_reason"] == "fuera de scope"


@pytest.mark.asyncio
async def test_escalated_conversation_skips_bot_on_next_message(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Once escalated, the next inbound from the student must not trigger RAG."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900030003"
    await _seed_student(postgres_url, phone)

    fake_answer_escalating = AsyncMock(
        return_value={
            "text": "Te derivo.",
            "tool_calls": [
                {"name": "escalate_to_human", "args": {"reason": "fuera de scope"}},
            ],
        }
    )
    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            fake_answer_escalating,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.esc2.bot.1"),
        ),
    ):
        await _process_async(
            _parsed("wamid.esc2.in.1", phone, text="quien eres"),
            "corr-esc2-1",
        )

    fake_answer_should_not_run = AsyncMock(
        return_value={"text": "this should never be sent", "tool_calls": []}
    )
    fake_send_should_not_run = AsyncMock(return_value="wamid.esc2.bot.2")
    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            fake_answer_should_not_run,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            fake_send_should_not_run,
        ),
    ):
        await _process_async(
            _parsed("wamid.esc2.in.2", phone, text="hola otra vez"),
            "corr-esc2-2",
        )

    fake_answer_should_not_run.assert_not_awaited()
    fake_send_should_not_run.assert_not_awaited()
    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.takeover
