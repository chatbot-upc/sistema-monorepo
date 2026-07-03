"""SW-49/SW-50/SW-51 (EP08) — consulta determinista de pagos.

Cuando el clasificador resuelve el mensaje a `consulta_pagos`, el worker responde
con los datos simulados de facturación del estudiante SIN pasar por el RAG.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from chatbot_api.core.settings import get_settings
from chatbot_api.models import (
    Conversation,
    Message,
    StudentBillingInstallment,
)
from chatbot_api.models.enums import BillingStatus, ConversationStatus, MessageRole
from chatbot_api.repositories.intent import intent_repository
from chatbot_api.repositories.student import student_repository
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.workers.conversation import _process_async


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV", "local")
    get_settings.cache_clear()


def _parsed(meta_id: str, phone: str, text: str = "tengo pagos pendientes?") -> dict[str, Any]:
    return ParsedInboundMessage(
        meta_message_id=meta_id,
        from_phone=phone,
        display_name="Billing Test",
        text=text,
        timestamp="1700000000",
    ).model_dump()


async def _seed_student(postgres_url: str, phone: str) -> None:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        await student_repository.upsert_by_phone(db, phone_e164=phone)
        await db.commit()
    await engine.dispose()


async def _seed_billing(
    postgres_url: str, phone: str, rows: list[dict[str, Any]]
) -> None:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        for r in rows:
            db.add(StudentBillingInstallment(phone_e164=phone, cycle="2026-1", **r))
        await db.commit()
    await engine.dispose()


async def _consulta_pagos_id(postgres_url: str) -> int:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        intent = await intent_repository.get_by_name(db, "consulta_pagos")
        assert intent is not None, "migración 0023 debe sembrar consulta_pagos"
        intent_id = intent.id
    await engine.dispose()
    return intent_id


def _classify_stub(intent_id: int) -> AsyncMock:
    return AsyncMock(
        return_value={
            "intent_id": intent_id,
            "intent_name": "consulta_pagos",
            "confidence": 0.9,
            "used_fallback": False,
            "sbert_intent_name": "consulta_pagos",
            "sbert_confidence": 0.9,
        }
    )


async def _read_conversation(postgres_url: str, phone: str) -> Conversation:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        conv = (
            await db.execute(
                select(Conversation).where(Conversation.student_phone == phone)
            )
        ).scalars().one()
    await engine.dispose()
    return conv


async def _read_bot_messages(postgres_url: str, conv_id: int) -> list[Message]:
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        msgs = (
            await db.execute(
                select(Message).where(
                    Message.conversation_id == conv_id,
                    Message.role == MessageRole.bot,
                )
            )
        ).scalars().all()
    await engine.dispose()
    return list(msgs)


@pytest.mark.asyncio
async def test_payment_intent_answers_with_billing_and_skips_rag(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900040001"
    await _seed_student(postgres_url, phone)
    await _seed_billing(
        postgres_url,
        phone,
        [
            {
                "number": 1,
                "concept": "Matrícula 2026-1",
                "amount": Decimal("850.00"),
                "due_date": date(2026, 3, 15),
                "status": BillingStatus.pagado,
                "paid_at": date(2026, 3, 10),
            },
            {
                "number": 2,
                "concept": "Cuota 1 - Pensión",
                "amount": Decimal("1850.00"),
                "due_date": date(2026, 8, 15),
                "status": BillingStatus.pendiente,
            },
        ],
    )
    intent_id = await _consulta_pagos_id(postgres_url)

    fake_rag = AsyncMock(return_value={"text": "no debería correr", "tool_calls": []})
    fake_send = AsyncMock(return_value="wamid.pay.bot.1")

    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            _classify_stub(intent_id),
        ),
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_rag),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            fake_send,
        ),
    ):
        await _process_async(_parsed("wamid.pay.in.1", phone), "corr-pay-1")

    # RAG jamás se invoca: la rama es determinista.
    fake_rag.assert_not_awaited()
    # El estudiante recibe la respuesta de facturación.
    fake_send.assert_awaited_once()
    assert fake_send.await_args.kwargs["to"] == phone
    body = fake_send.await_args.kwargs["body"]
    assert "Estado de tus pagos" in body
    assert "Próxima cuota" in body
    assert "S/ 1,850.00" in body

    # No escala: sigue abierta y con un mensaje del bot persistido.
    conv = await _read_conversation(postgres_url, phone)
    assert conv.status == ConversationStatus.abierta
    bot_msgs = await _read_bot_messages(postgres_url, conv.id)
    assert any("Estado de tus pagos" in m.content for m in bot_msgs)


@pytest.mark.asyncio
async def test_payment_intent_all_paid(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900040002"
    await _seed_student(postgres_url, phone)
    await _seed_billing(
        postgres_url,
        phone,
        [
            {
                "number": 1,
                "concept": "Matrícula 2026-1",
                "amount": Decimal("850.00"),
                "due_date": date(2026, 3, 15),
                "status": BillingStatus.pagado,
                "paid_at": date(2026, 3, 10),
            },
        ],
    )
    intent_id = await _consulta_pagos_id(postgres_url)

    fake_send = AsyncMock(return_value="wamid.pay.bot.2")
    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            _classify_stub(intent_id),
        ),
        patch(
            "chatbot_api.workers.conversation.rag_service.answer",
            AsyncMock(return_value={"text": "x", "tool_calls": []}),
        ),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            fake_send,
        ),
    ):
        await _process_async(_parsed("wamid.pay.in.2", phone), "corr-pay-2")

    fake_send.assert_awaited_once()
    assert "al día" in fake_send.await_args.kwargs["body"].lower()


@pytest.mark.asyncio
async def test_payment_intent_no_billing_returns_canned(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    phone = "+51900040003"
    await _seed_student(postgres_url, phone)  # sin facturación sembrada
    intent_id = await _consulta_pagos_id(postgres_url)

    fake_rag = AsyncMock(return_value={"text": "no corre", "tool_calls": []})
    fake_send = AsyncMock(return_value="wamid.pay.bot.3")
    with (
        patch(
            "chatbot_api.workers.conversation.intent_classifier_service.classify",
            _classify_stub(intent_id),
        ),
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_rag),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message",
            fake_send,
        ),
    ):
        await _process_async(_parsed("wamid.pay.in.3", phone), "corr-pay-3")

    fake_rag.assert_not_awaited()
    fake_send.assert_awaited_once()
    assert "no encontré" in fake_send.await_args.kwargs["body"].lower()
