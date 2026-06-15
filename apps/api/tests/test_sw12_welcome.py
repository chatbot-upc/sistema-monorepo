"""SW-12 HU03 tests — welcome message on first contact."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.workers.conversation import _get_welcome_text, _process_async


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


def _parsed(meta_id: str, phone: str, text: str = "hola") -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Welcome Test",
        text=text,
        timestamp="1700000000",
    ).model_dump()


def test_welcome_template_mentions_topics() -> None:
    """The welcome text should list the topics the bot covers (matricula, pagos, ingles, becas)."""
    text = _get_welcome_text().lower()
    assert "matr" in text  # matrícula
    assert "pago" in text
    assert any(kw in text for kw in ("inglés", "ingles"))
    assert "beca" in text


@pytest.mark.asyncio
async def test_first_contact_sends_welcome_then_rag(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900012001"
    welcome_text = _get_welcome_text()

    rag_text = "Matricula: revisa el cronograma."
    sent_bodies: list[str] = []

    async def _fake_send(*, to: str, body: str, context: dict | None = None) -> str:
        sent_bodies.append(body)
        return f"wamid.first.bot.{len(sent_bodies)}"

    fake_answer = AsyncMock(
        return_value={
            "text": rag_text,
            "tool_calls": [],
            "input_tokens": 10,
            "output_tokens": 5,
        }
    )

    with (
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            side_effect=_fake_send,
        ),
    ):
        await _process_async(_parsed("wamid.first.1", phone), "corr-first")

    # 2 outbound sends: welcome first, then RAG reply.
    assert sent_bodies == [welcome_text, rag_text]

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        msgs = (
            (
                await verify.execute(
                    select(Message)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(Conversation.student_phone == phone)
                    .order_by(Message.created_at.asc(), Message.id.asc())
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()

    assert [m.role for m in msgs] == [
        MessageRole.student,
        MessageRole.bot,
        MessageRole.bot,
    ]
    assert msgs[1].content == welcome_text
    assert msgs[2].content == rag_text
    # Welcome row has the outbound id but no RAG metadata.
    assert msgs[1].latency_ms is None
    assert msgs[1].input_tokens is None
    # RAG row carries the model metadata.
    assert msgs[2].model_used == get_settings().openai_model


@pytest.mark.asyncio
async def test_returning_student_no_welcome(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-existing student receives only the RAG reply on the second message."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900012002"

    # Pre-create the student.
    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        await setup_db.commit()
    await setup_engine.dispose()

    sent_bodies: list[str] = []

    async def _fake_send(*, to: str, body: str, context: dict | None = None) -> str:
        sent_bodies.append(body)
        return f"wamid.ret.bot.{len(sent_bodies)}"

    fake_answer = AsyncMock(
        return_value={"text": "respuesta normal", "tool_calls": []}
    )

    with (
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            side_effect=_fake_send,
        ),
    ):
        await _process_async(_parsed("wamid.ret.in.1", phone), "corr-ret")

    assert sent_bodies == ["respuesta normal"]

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        msgs = (
            (
                await verify.execute(
                    select(Message)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(Conversation.student_phone == phone)
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()
    inbound = sum(1 for m in msgs if m.role == MessageRole.student)
    bot = sum(1 for m in msgs if m.role == MessageRole.bot)
    assert inbound == 1
    assert bot == 1
