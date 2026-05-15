"""SW-10 HU01 tests — bot RAG answer + outbound to WhatsApp Cloud API."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import ConversationStatus, MessageRole
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.services import whatsapp_service
from chatbot_api.workers.conversation import _process_async

# ----- whatsapp_service.send_message unit tests -----------------------------------


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_send_message_dev_bypass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "")
    get_settings.cache_clear()
    meta_id = await whatsapp_service.send_message(to="+51900000001", body="hola")
    assert meta_id.startswith("wamid.dev.")


@pytest.mark.asyncio
async def test_send_message_real_post(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("META_ACCESS_TOKEN", "TOKEN-ABC")
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "PHONE-1")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v21.0")
    get_settings.cache_clear()

    fake_resp = httpx.Response(
        200,
        json={
            "messaging_product": "whatsapp",
            "contacts": [{"input": "51900000001", "wa_id": "51900000001"}],
            "messages": [{"id": "wamid.outbound.123"}],
        },
        request=httpx.Request("POST", "https://graph.facebook.com/v21.0/PHONE-1/messages"),
    )
    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=fake_resp)
    monkeypatch.setattr(whatsapp_service, "_get_client", lambda: fake_client)

    meta_id = await whatsapp_service.send_message(to="+51900000001", body="hola")
    assert meta_id == "wamid.outbound.123"

    call = fake_client.post.await_args
    url = call.args[0]
    payload = call.kwargs["json"]
    headers = call.kwargs["headers"]
    assert url == "https://graph.facebook.com/v21.0/PHONE-1/messages"
    assert payload["to"] == "51900000001"  # leading + stripped
    assert payload["text"] == {"body": "hola"}
    assert headers["Authorization"] == "Bearer TOKEN-ABC"


# ----- worker E2E with mocked RAG + WA --------------------------------------------


def _parsed(meta_id: str = "wamid.in.1", phone: str = "+51900000700") -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Test SW10",
        text="cuando inicia matricula?",
        timestamp="1700000000",
    ).model_dump()


@pytest.mark.asyncio
async def test_worker_persists_student_and_bot(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    fake_answer = AsyncMock(
        return_value={
            "text": "Matricula inicia el 1 de junio.",
            "tool_calls": [{"name": "search_knowledge_base", "args": {"query": "matricula"}}],
            "input_tokens": 120,
            "output_tokens": 30,
        }
    )
    fake_send = AsyncMock(return_value="wamid.bot.out.1")

    with (
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
        patch("chatbot_api.workers.conversation.whatsapp_service.send_message", fake_send),
    ):
        await _process_async(_parsed(), "corr-sw10-1")

    fake_answer.assert_awaited_once()
    fake_send.assert_awaited_once_with(
        to="+51900000700", body="Matricula inicia el 1 de junio."
    )

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        msgs = (
            (
                await verify.execute(
                    select(Message)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(Conversation.student_phone == "+51900000700")
                    .order_by(Message.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()

    assert [m.role for m in msgs] == [MessageRole.student, MessageRole.bot]
    bot = msgs[1]
    assert bot.content == "Matricula inicia el 1 de junio."
    assert bot.meta_message_id == "wamid.bot.out.1"
    assert bot.input_tokens == 120
    assert bot.output_tokens == 30
    assert bot.model_used == get_settings().openai_model
    assert bot.latency_ms is not None and bot.latency_ms >= 0


@pytest.mark.asyncio
async def test_worker_skips_bot_when_takeover(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If conversation is in takeover, RAG/send must not run.

    Uses an independent committed engine for setup so the worker's own engine
    sees the takeover state (transactional db_session fixture would be invisible).
    """
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900000800"

    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        conv, _ = await conversation_repository.get_or_create_open(setup_db, phone)
        conv.status = ConversationStatus.takeover
        await setup_db.commit()
    await setup_engine.dispose()

    fake_answer = AsyncMock(return_value={"text": "should not be called"})
    fake_send = AsyncMock(return_value="wamid.never")

    try:
        with (
            patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
            patch("chatbot_api.workers.conversation.whatsapp_service.send_message", fake_send),
        ):
            await _process_async(
                _parsed(meta_id="wamid.takeover.1", phone=phone), "corr-takeover"
            )

        fake_answer.assert_not_awaited()
        fake_send.assert_not_awaited()

        verify_engine = create_async_engine(postgres_url)
        verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
        async with verify_factory() as verify:
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
        await verify_engine.dispose()
        inbound_count = sum(1 for m in msgs if m.role == MessageRole.student)
        bot_count = sum(1 for m in msgs if m.role == MessageRole.bot)
        assert inbound_count == 1
        assert bot_count == 0
    finally:
        cleanup_engine = create_async_engine(postgres_url)
        cleanup_factory = async_sessionmaker(cleanup_engine, expire_on_commit=False)
        async with cleanup_factory() as cleanup:
            await cleanup.execute(
                Conversation.__table__.delete().where(
                    Conversation.student_phone == phone
                )
            )
            from chatbot_api.models import Student

            await cleanup.execute(
                Student.__table__.delete().where(Student.phone_e164 == phone)
            )
            await cleanup.commit()
        await cleanup_engine.dispose()


@pytest.mark.asyncio
async def test_message_repository_create_bot(db_session: Any) -> None:
    """Sanity check create_bot persists all metadata fields."""
    from tests.factories import make_conversation, make_student

    await make_student(db_session, phone="+51900000900", display_name="repo test")
    conv = await make_conversation(db_session, student_phone="+51900000900")

    bot = await message_repository.create_bot(
        db_session,
        conversation_id=conv.id,
        content="answer",
        retrieved_chunks=[{"name": "search_kb", "args": {"q": "x"}}],
        input_tokens=10,
        output_tokens=5,
        latency_ms=42,
        model_used="gpt-4o-mini",
        meta_message_id="wamid.test.bot",
    )
    assert bot.role == MessageRole.bot
    assert bot.retrieved_chunks == [{"name": "search_kb", "args": {"q": "x"}}]
    assert bot.input_tokens == 10
    assert bot.output_tokens == 5
    assert bot.latency_ms == 42
    assert bot.model_used == "gpt-4o-mini"
    assert bot.meta_message_id == "wamid.test.bot"
