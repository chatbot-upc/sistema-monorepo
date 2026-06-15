"""Responder/citar un mensaje específico (reply/quote estilo WhatsApp context).

Cubre las 3 capas:
- Entrante: el webhook parsea context.id → ParsedInboundMessage.context_wamid.
- Worker: el inbound citado persiste in_reply_to_id + quoted e inyecta el mensaje
  citado al user_text del agente RAG.
- Saliente: el admin cita desde el CRM → send_message recibe context={message_id}
  y el mensaje persiste in_reply_to_id + quoted; cita cruzada de conversación → 422.
- Lectura: MessageRead expone el snapshot quoted.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Message
from chatbot_api.models.enums import ConversationStatus, MessageRole
from chatbot_api.schemas.message import MessageRead
from chatbot_api.schemas.whatsapp import (
    ParsedInboundMessage,
    WhatsAppWebhookPayload,
)
from chatbot_api.services.whatsapp_webhook_service import extract_messages
from chatbot_api.workers.conversation import _process_async

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


# ── Capa 1: parseo del context entrante ───────────────────────────────


def test_extract_messages_parses_context_wamid() -> None:
    payload = WhatsAppWebhookPayload.model_validate(
        {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA",
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messaging_product": "whatsapp",
                                "contacts": [
                                    {"wa_id": "51900000001", "profile": {"name": "Ana"}}
                                ],
                                "messages": [
                                    {
                                        "from": "51900000001",
                                        "id": "wamid.reply.1",
                                        "timestamp": "1700000000",
                                        "type": "text",
                                        "text": {"body": "Sí, confirmo"},
                                        "context": {
                                            "id": "wamid.original.1",
                                            "from": "15550000000",
                                        },
                                    }
                                ],
                            },
                        }
                    ],
                }
            ],
        }
    )
    parsed = extract_messages(payload)
    assert len(parsed) == 1
    assert parsed[0].context_wamid == "wamid.original.1"


def test_extract_messages_without_context_is_none() -> None:
    payload = WhatsAppWebhookPayload.model_validate(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "contacts": [{"wa_id": "51900000002"}],
                                "messages": [
                                    {
                                        "from": "51900000002",
                                        "id": "wamid.plain.1",
                                        "timestamp": "1700000000",
                                        "type": "text",
                                        "text": {"body": "hola"},
                                    }
                                ],
                            }
                        }
                    ]
                }
            ]
        }
    )
    parsed = extract_messages(payload)
    assert parsed[0].context_wamid is None


# ── Capa 4: lectura — MessageRead expone el snapshot ──────────────────


def test_message_read_exposes_quoted_snapshot() -> None:
    ns = SimpleNamespace(
        id=10,
        conversation_id=1,
        role=MessageRole.admin,
        content="Claro, te ayudo",
        intent_id=None,
        input_tokens=None,
        output_tokens=None,
        model_used=None,
        latency_ms=None,
        created_at=datetime.now(),
        in_reply_to_id=7,
        quoted={
            "id": 7,
            "role": "student",
            "content": "¿Cuándo es la matrícula?",
            "created_at": "2026-06-14T10:00:00",
        },
    )
    mr = MessageRead.model_validate(ns)
    assert mr.in_reply_to_id == 7
    assert mr.quoted is not None
    assert mr.quoted.id == 7
    assert mr.quoted.role == MessageRole.student
    assert mr.quoted.content == "¿Cuándo es la matrícula?"


# ── Capa 3: saliente — admin cita desde el CRM ────────────────────────


@pytest.fixture
def _stub_outbound(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Captura las llamadas a send_message y silencia los eventos."""
    from chatbot_api.services import conversation_service, whatsapp_service

    fake_send = AsyncMock(return_value="wamid.admin.out")
    monkeypatch.setattr(whatsapp_service, "send_message", fake_send)

    async def _noop(event_type: str, data: dict) -> None:
        return None

    monkeypatch.setattr(conversation_service, "publish_event", _noop)
    return fake_send


async def test_admin_reply_builds_context_and_persists_quoted(
    client: AsyncClient, db_session: AsyncSession, _stub_outbound: AsyncMock
) -> None:
    student = await factories.make_student(db_session, phone="+51900300001")
    conv = await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.takeover,
    )
    original = Message(
        conversation_id=conv.id,
        role=MessageRole.student,
        content="¿Cuándo es la matrícula?",
        retrieved_chunks=[],
        meta_message_id="wamid.student.orig",
    )
    db_session.add(original)
    await db_session.flush()

    resp = await client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"body": "El 20 de julio", "in_reply_to_id": original.id},
        headers=DEV_USER_HEADER,
    )
    assert resp.status_code == 201, resp.text

    # send_message recibió el context con el wamid del mensaje citado.
    assert _stub_outbound.call_args.kwargs["context"] == {
        "message_id": "wamid.student.orig"
    }

    # El mensaje admin persiste la FK y el snapshot congelado.
    admin_msg = (
        await db_session.execute(
            select(Message).where(
                Message.conversation_id == conv.id,
                Message.role == MessageRole.admin,
            )
        )
    ).scalars().one()
    assert admin_msg.in_reply_to_id == original.id
    assert admin_msg.quoted is not None
    assert admin_msg.quoted["id"] == original.id
    assert admin_msg.quoted["content"] == "¿Cuándo es la matrícula?"


async def test_admin_reply_cross_conversation_rejected(
    client: AsyncClient, db_session: AsyncSession, _stub_outbound: AsyncMock
) -> None:
    student_a = await factories.make_student(db_session, phone="+51900300002")
    conv_a = await factories.make_conversation(
        db_session, student_phone=student_a.phone_e164
    )
    student_b = await factories.make_student(db_session, phone="+51900300003")
    conv_b = await factories.make_conversation(
        db_session, student_phone=student_b.phone_e164
    )
    foreign = await factories.make_message(db_session, conversation_id=conv_b.id)

    resp = await client.post(
        f"/api/v1/conversations/{conv_a.id}/messages",
        json={"body": "cita inválida", "in_reply_to_id": foreign.id},
        headers=DEV_USER_HEADER,
    )
    assert resp.status_code == 422
    _stub_outbound.assert_not_called()


# ── Capa 1+2: worker — persiste cita e inyecta contexto al agente ─────


async def test_worker_inbound_reply_persists_and_injects_context(
    db_session: AsyncSession,
    postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from chatbot_api.repositories.conversation import conversation_repository
    from chatbot_api.repositories.student import student_repository

    phone = "+51900300010"
    bot_wamid = "wamid.bot.tocite"

    # Pre-sembrar: student + conversación abierta + un mensaje del bot citable.
    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164=phone)
        conv, _, _ = await conversation_repository.get_or_create_open(setup_db, phone)
        setup_db.add(
            Message(
                conversation_id=conv.id,
                role=MessageRole.bot,
                content="La matrícula abre el 20 de julio.",
                retrieved_chunks=[],
                meta_message_id=bot_wamid,
            )
        )
        await setup_db.commit()
    await setup_engine.dispose()

    parsed = ParsedInboundMessage(
        meta_message_id="wamid.student.reply",
        from_phone=phone,
        display_name="Ana",
        text="No entendí esa fecha",
        timestamp="1700000000",
        context_wamid=bot_wamid,
    ).model_dump()

    fake_answer = AsyncMock(return_value={"text": "Te explico", "tool_calls": []})
    fake_send = AsyncMock(return_value="wamid.bot.reply")
    with (
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message", fake_send
        ),
    ):
        await _process_async(parsed, "corr-reply")

    # El agente recibió el bloque con el mensaje citado anclado.
    injected = fake_answer.call_args.kwargs["user_text"]
    assert "La matrícula abre el 20 de julio." in injected
    assert "No entendí esa fecha" in injected

    # El inbound persistió la FK y el snapshot.
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        inbound = (
            await verify.execute(
                select(Message).where(
                    Message.meta_message_id == "wamid.student.reply"
                )
            )
        ).scalars().one()
        cited = (
            await verify.execute(
                select(Message).where(Message.meta_message_id == bot_wamid)
            )
        ).scalars().one()
    await engine.dispose()

    assert inbound.in_reply_to_id == cited.id
    assert inbound.quoted is not None
    assert inbound.quoted["content"] == "La matrícula abre el 20 de julio."


# ── Debounce: consolidación del lote + cita solo si varios mensajes ───


async def _seed_student_batch(
    db_session: AsyncSession, *, phone: str, contents: list[str]
) -> list[Message]:
    student = await factories.make_student(db_session, phone=phone)
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    msgs: list[Message] = []
    for i, content in enumerate(contents):
        m = Message(
            conversation_id=conv.id,
            role=MessageRole.student,
            content=content,
            retrieved_chunks=[],
            meta_message_id=f"wamid.batch.{phone[-3:]}.{i}",
        )
        db_session.add(m)
        msgs.append(m)
    await db_session.flush()
    return msgs


def _patch_reply_deps(
    monkeypatch: pytest.MonkeyPatch,
    answer_text: str,
    tool_calls: list[dict] | None = None,
) -> AsyncMock:
    from chatbot_api.workers import conversation as worker

    fake_answer = AsyncMock(
        return_value={"text": answer_text, "tool_calls": tool_calls or []}
    )
    fake_send = AsyncMock(return_value="wamid.bot.out")
    monkeypatch.setattr(worker.rag_service, "answer", fake_answer)
    monkeypatch.setattr(worker.whatsapp_service, "send_message", fake_send)
    monkeypatch.setattr(worker.whatsapp_service, "mark_read", AsyncMock())
    monkeypatch.setattr(
        worker.student_profile_service,
        "get_profile_scope",
        AsyncMock(return_value=(None, None)),
    )

    async def _noop(*a: object, **k: object) -> None:
        return None

    monkeypatch.setattr(worker, "publish_event", _noop)
    return fake_send


async def test_run_reply_consolidates_and_quotes_message_chosen_by_agent(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chatbot_api.workers import conversation as worker

    msgs = await _seed_student_batch(
        db_session,
        phone="+51900400001",
        contents=["hola", "qué tal", "¿cuándo es la matrícula?"],
    )
    # El agente decide citar el mensaje 3 (el de la intención real).
    fake_send = _patch_reply_deps(
        monkeypatch,
        "El 20 de julio",
        tool_calls=[{"name": "reply_to_message", "args": {"message_number": 3}}],
    )
    fake_answer = worker.rag_service.answer  # type: ignore[attr-defined]

    await worker._run_reply(
        db_session,
        conversation_id=msgs[0].conversation_id,
        phone="+51900400001",
        batch_ids=[m.id for m in msgs],
        correlation_id="c-batch",
    )

    # Consolidó los 3 mensajes numerados en un solo turno para el agente.
    user_text = fake_answer.call_args.kwargs["user_text"]
    assert "hola" in user_text and "¿cuándo es la matrícula?" in user_text

    # Citó el mensaje que ELIGIÓ el agente (el 3), no una posición fija.
    assert fake_send.call_args.kwargs["context"] == {
        "message_id": msgs[2].meta_message_id
    }
    bot = (
        await db_session.execute(
            select(Message).where(
                Message.conversation_id == msgs[0].conversation_id,
                Message.role == MessageRole.bot,
            )
        )
    ).scalars().one()
    assert bot.in_reply_to_id == msgs[2].id
    assert bot.quoted is not None and bot.quoted["id"] == msgs[2].id

    # Mostró "escribiendo…" sobre el último mensaje antes de responder.
    worker.whatsapp_service.mark_read.assert_any_await(
        message_id=msgs[-1].meta_message_id, typing=True
    )


async def test_run_reply_no_quote_when_agent_does_not_choose(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chatbot_api.workers import conversation as worker

    msgs = await _seed_student_batch(
        db_session,
        phone="+51900400003",
        contents=["hola", "buenas"],
    )
    # Varios mensajes, pero el agente NO llama a reply_to_message → no cita.
    fake_send = _patch_reply_deps(monkeypatch, "¡Hola! ¿En qué te ayudo?")

    await worker._run_reply(
        db_session,
        conversation_id=msgs[0].conversation_id,
        phone="+51900400003",
        batch_ids=[m.id for m in msgs],
        correlation_id="c-noquote",
    )

    assert fake_send.call_args.kwargs["context"] is None
    bot = (
        await db_session.execute(
            select(Message).where(
                Message.conversation_id == msgs[0].conversation_id,
                Message.role == MessageRole.bot,
            )
        )
    ).scalars().one()
    assert bot.in_reply_to_id is None
    assert bot.quoted is None


async def test_run_reply_single_message_does_not_quote(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chatbot_api.workers import conversation as worker

    msgs = await _seed_student_batch(
        db_session, phone="+51900400002", contents=["¿Cuándo es la matrícula?"]
    )
    fake_send = _patch_reply_deps(monkeypatch, "El 20 de julio")

    await worker._run_reply(
        db_session,
        conversation_id=msgs[0].conversation_id,
        phone="+51900400002",
        batch_ids=[msgs[0].id],
        correlation_id="c-single",
    )

    # Un solo mensaje → respuesta normal, sin cita.
    assert fake_send.call_args.kwargs["context"] is None
    bot = (
        await db_session.execute(
            select(Message).where(
                Message.conversation_id == msgs[0].conversation_id,
                Message.role == MessageRole.bot,
            )
        )
    ).scalars().one()
    assert bot.in_reply_to_id is None
    assert bot.quoted is None
