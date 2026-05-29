"""SW-18 + SW-25 — conversation memory for the RAG agent."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.repositories.conversation import conversation_repository
from chatbot_api.repositories.message import message_repository
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


# ----- repository -----------------------------------------------------------


@pytest.mark.asyncio
async def test_list_recent_respects_conversation_isolation(
    db_session: AsyncSession,
) -> None:
    """Two conversations must not bleed messages into each other."""
    from tests.factories import make_conversation, make_message, make_student

    await make_student(db_session, phone="+51900018001")
    await make_student(db_session, phone="+51900018002")
    conv_a = await make_conversation(db_session, student_phone="+51900018001")
    conv_b = await make_conversation(db_session, student_phone="+51900018002")
    await make_message(db_session, conversation_id=conv_a.id, content="msg A1")
    await make_message(db_session, conversation_id=conv_a.id, content="msg A2")
    await make_message(db_session, conversation_id=conv_b.id, content="msg B1")
    await db_session.flush()

    msgs_a = await message_repository.list_recent_for_conversation(
        db_session,
        conversation_id=conv_a.id,
        since=datetime.now() - timedelta(hours=24),
    )
    msgs_b = await message_repository.list_recent_for_conversation(
        db_session,
        conversation_id=conv_b.id,
        since=datetime.now() - timedelta(hours=24),
    )
    assert [m.content for m in msgs_a] == ["msg A1", "msg A2"]
    assert [m.content for m in msgs_b] == ["msg B1"]


@pytest.mark.asyncio
async def test_list_recent_skips_messages_outside_window(
    db_session: AsyncSession,
) -> None:
    """Messages older than `since` must NOT come back."""
    from tests.factories import make_conversation, make_student

    await make_student(db_session, phone="+51900018010")
    conv = await make_conversation(db_session, student_phone="+51900018010")
    now = datetime.now()
    db_session.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.student,
            content="old",
            retrieved_chunks=[],
            created_at=now - timedelta(hours=30),
        )
    )
    db_session.add(
        Message(
            conversation_id=conv.id,
            role=MessageRole.student,
            content="fresh",
            retrieved_chunks=[],
            created_at=now - timedelta(minutes=5),
        )
    )
    await db_session.flush()

    msgs = await message_repository.list_recent_for_conversation(
        db_session,
        conversation_id=conv.id,
        since=now - timedelta(hours=24),
    )
    assert [m.content for m in msgs] == ["fresh"]


@pytest.mark.asyncio
async def test_list_recent_excludes_after_id(db_session: AsyncSession) -> None:
    from tests.factories import make_conversation, make_message, make_student

    await make_student(db_session, phone="+51900018020")
    conv = await make_conversation(db_session, student_phone="+51900018020")
    m1 = await make_message(db_session, conversation_id=conv.id, content="m1")
    m2 = await make_message(db_session, conversation_id=conv.id, content="m2")
    m3 = await make_message(db_session, conversation_id=conv.id, content="m3")
    await db_session.flush()

    msgs = await message_repository.list_recent_for_conversation(
        db_session,
        conversation_id=conv.id,
        since=datetime.now() - timedelta(hours=24),
        exclude_after_id=m3.id,
    )
    assert [m.content for m in msgs] == ["m1", "m2"]
    assert all(m.id < m3.id for m in msgs)
    # idempotent for sanity
    assert {m.id for m in msgs} == {m1.id, m2.id}


# ----- worker E2E -----------------------------------------------------------


def _parsed(meta_id: str, phone: str, text: str) -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Memory Test",
        text=text,
        timestamp="1700000000",
    ).model_dump()


@pytest.mark.asyncio
async def test_second_turn_feeds_history_to_rag(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Second message in same conv must pass history to rag_service.answer."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900018100"

    # Pre-create student + conv + 2 previous messages (student + bot) so the
    # incoming turn finds a real history.
    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        conv, _ = await conversation_repository.get_or_create_open(setup_db, phone)
        await message_repository.create_inbound(
            setup_db,
            conversation_id=conv.id,
            content="que cursos lleva ingenieria de software en el ciclo 3",
            meta_message_id="wamid.mem.prev.in",
        )
        await message_repository.create_bot(
            setup_db,
            conversation_id=conv.id,
            content="IHC, Arquitectura, Calculo I... (Fuentes: doc_id=109)",
            meta_message_id="wamid.mem.prev.bot",
        )
        await setup_db.commit()
    await setup_engine.dispose()

    captured: dict[str, Any] = {}

    async def _capturing_answer(
        *, user_text: str, correlation_id: str, history: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        captured["user_text"] = user_text
        captured["history"] = list(history or [])
        return {"text": "Ciclo 4...", "tool_calls": []}

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            side_effect=_capturing_answer,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.mem.bot.next"),
        ),
    ):
        await _process_async(
            _parsed("wamid.mem.in.next", phone, "y en el siguiente ciclo?"),
            "corr-mem-1",
        )

    assert captured["user_text"] == "y en el siguiente ciclo?"
    assert len(captured["history"]) == 2
    assert captured["history"][0] == {
        "role": "user",
        "content": "que cursos lleva ingenieria de software en el ciclo 3",
    }
    assert captured["history"][1]["role"] == "assistant"
    assert "IHC" in captured["history"][1]["content"]


@pytest.mark.asyncio
async def test_first_turn_history_is_empty(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A brand-new conversation has nothing to remember."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900018200"
    captured: dict[str, Any] = {}

    async def _capturing_answer(
        *, user_text: str, correlation_id: str, history: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        captured["history"] = list(history or [])
        return {"text": "primera respuesta", "tool_calls": []}

    sent: list[str] = []

    async def _fake_send(*, to: str, body: str) -> str:
        sent.append(body)
        return f"wamid.mem.first.{len(sent)}"

    with (
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            side_effect=_capturing_answer,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            side_effect=_fake_send,
        ),
    ):
        await _process_async(
            _parsed("wamid.mem.first.in", phone, "hola, una consulta"),
            "corr-mem-first",
        )

    # First contact: only the welcome + this turn exist, both AFTER inbound.id,
    # so the captured history must be empty.
    assert captured["history"] == []

    # Sanity: rows did get persisted.
    verify_engine = create_async_engine(postgres_url)
    verify_factory = async_sessionmaker(verify_engine, expire_on_commit=False)
    async with verify_factory() as verify:
        rows = (
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
    assert len(rows) >= 2  # inbound + welcome + bot reply
