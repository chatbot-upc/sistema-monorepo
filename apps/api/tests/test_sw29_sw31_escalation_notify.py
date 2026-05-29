"""SW-29 + SW-31 — escalation side effects.

SW-29: notify the student that the conversation has been handed off.
SW-31: broadcast a push to every active admin with the context payload.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Conversation, Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.workers.conversation import _process_async


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()


def _parsed(meta_id: str, phone: str, text: str = "hola") -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Escalation Notify Test",
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


async def _resolve_solicita_humano_id(postgres_url: str) -> int:
    from chatbot_api.repositories.intent import intent_repository

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        intent = await intent_repository.get_by_name(db, "solicita_humano")
        assert intent is not None
        intent_id = intent.id
    await engine.dispose()
    return intent_id


async def _read_messages(postgres_url: str, phone: str) -> list[Message]:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        rows: list[Message] = list(
            (
                await verify.execute(
                    select(Message)
                    .join(Conversation, Conversation.id == Message.conversation_id)
                    .where(Conversation.student_phone == phone)
                    .order_by(Message.id.asc())
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()
    return rows


@pytest.mark.asyncio
async def test_sbert_path_notifies_student_and_pushes_admin(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900029001"
    await _seed_student(postgres_url, phone)
    intent_id = await _resolve_solicita_humano_id(postgres_url)

    sbert_classify = AsyncMock(
        return_value={
            "intent_id": intent_id,
            "intent_name": "solicita_humano",
            "confidence": 0.9,
            "used_fallback": False,
            "sbert_intent_name": "solicita_humano",
            "sbert_confidence": 0.9,
        }
    )

    sent_payloads: list[dict[str, str]] = []

    async def _fake_send(*, to: str, body: str) -> str:
        sent_payloads.append({"to": to, "body": body})
        return f"wamid.sw29.{len(sent_payloads)}"

    push_calls: list[dict[str, Any]] = []

    async def _fake_push(
        db: AsyncSession,
        *,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> int:
        push_calls.append({"title": title, "body": body, "data": data or {}})
        return 1

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            sbert_classify,
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            side_effect=_fake_send,
        ),
        patch(
            "chatbot_api.workers.conversation.push_service.notify_all_admins",
            side_effect=_fake_push,
        ),
    ):
        await _process_async(
            _parsed("wamid.sw29.in.1", phone, text="pasame con un asesor por favor"),
            "corr-sw29-sbert",
        )

    # Student got exactly one notice (the SBERT path doesn't run the RAG).
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["to"] == phone
    assert "asesor humano" in sent_payloads[0]["body"].lower()

    # Push fired with full context.
    assert len(push_calls) == 1
    data = push_calls[0]["data"]
    assert data["type"] == "escalation"
    assert data["student_phone"] == phone
    assert data["source"] == "intent_classifier"
    assert data["url"].startswith("/conversations/")
    assert push_calls[0]["body"].startswith("pasame con un asesor")

    # The notice is persisted as a bot message so the admin can see it in the
    # conversation thread when they take over.
    msgs = await _read_messages(postgres_url, phone)
    bot_msgs = [m for m in msgs if m.role == MessageRole.bot]
    assert any("asesor humano" in m.content.lower() for m in bot_msgs)


@pytest.mark.asyncio
async def test_llm_path_pushes_admin_without_extra_notice(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM already produced its own answer mentioning the handoff — don't
    follow up with a second canned message. Just push admins."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900029002"
    await _seed_student(postgres_url, phone)

    stub_intent = AsyncMock(
        return_value={
            "intent_id": None,
            "intent_name": "otros",
            "confidence": 0.0,
            "used_fallback": False,
            "sbert_intent_name": None,
            "sbert_confidence": 0.0,
        }
    )
    fake_answer = AsyncMock(
        return_value={
            "text": "No tengo info, te derivo con un asesor humano.",
            "tool_calls": [
                {"name": "escalate_to_human", "args": {"reason": "no info"}},
            ],
        }
    )

    sent_payloads: list[dict[str, str]] = []

    async def _fake_send(*, to: str, body: str) -> str:
        sent_payloads.append({"to": to, "body": body})
        return f"wamid.sw29.llm.{len(sent_payloads)}"

    push_calls: list[dict[str, Any]] = []

    async def _fake_push(
        db: AsyncSession,
        *,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> int:
        push_calls.append({"title": title, "body": body, "data": data or {}})
        return 1

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            stub_intent,
        ),
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_answer
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            side_effect=_fake_send,
        ),
        patch(
            "chatbot_api.workers.conversation.push_service.notify_all_admins",
            side_effect=_fake_push,
        ),
    ):
        await _process_async(
            _parsed("wamid.sw29.llm.in", phone, text="pregunta rara"),
            "corr-sw29-llm",
        )

    # Only the LLM-generated answer was sent (no extra canned notice).
    assert len(sent_payloads) == 1
    assert "asesor humano" in sent_payloads[0]["body"].lower()
    assert push_calls[0]["data"]["source"] == "llm"
    assert push_calls[0]["data"]["reason"] == "no info"


@pytest.mark.asyncio
async def test_normal_answer_does_not_push_admin(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful RAG response (no escalation) must not bother the admin."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900029003"
    await _seed_student(postgres_url, phone)

    stub_intent = AsyncMock(
        return_value={
            "intent_id": None,
            "intent_name": "consulta_mallas",
            "confidence": 0.7,
            "used_fallback": False,
            "sbert_intent_name": "consulta_mallas",
            "sbert_confidence": 0.7,
        }
    )
    fake_answer = AsyncMock(
        return_value={"text": "Aquí los cursos: ...", "tool_calls": []}
    )

    push_calls: list[Any] = []

    async def _fake_push(db: AsyncSession, **kwargs: Any) -> int:
        push_calls.append(kwargs)
        return 1

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            stub_intent,
        ),
        patch(
            "chatbot_api.workers.conversation.rag_service.answer", fake_answer
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            AsyncMock(return_value="wamid.normal.bot"),
        ),
        patch(
            "chatbot_api.workers.conversation.push_service.notify_all_admins",
            side_effect=_fake_push,
        ),
    ):
        await _process_async(
            _parsed("wamid.normal.in", phone, text="cuantos cursos lleva mineria"),
            "corr-normal",
        )

    assert push_calls == []
