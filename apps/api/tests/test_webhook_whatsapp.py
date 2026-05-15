"""SW-13 HU04 tests — WhatsApp webhook + idempotencia + dispatch a Celery."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api import webhooks as webhook_module
from chatbot_api.core.settings import get_settings
from chatbot_api.models import Message, Student
from chatbot_api.schemas.whatsapp import ParsedInboundMessage
from chatbot_api.workers.conversation import _process_async

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


def _sample_payload(
    *,
    wa_id: str = "51900000001",
    msg_id: str = "wamid.test.1",
    text: str = "Hola, dudas sobre matricula",
    name: str = "Maria Paula",
) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "51999999999",
                                "phone_number_id": "PHONE_ID",
                            },
                            "contacts": [
                                {"wa_id": wa_id, "profile": {"name": name}},
                            ],
                            "messages": [
                                {
                                    "from": wa_id,
                                    "id": msg_id,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": text},
                                },
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _sign(raw: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def _override_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Meta secrets and isolate the Celery dispatch."""
    monkeypatch.setenv("META_APP_SECRET", APP_SECRET)
    monkeypatch.setenv("META_VERIFY_TOKEN", VERIFY_TOKEN)
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


@pytest.fixture
def patched_dispatch(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace process_incoming_message.delay so HTTP tests don't hit Redis."""
    fake = MagicMock(name="process_incoming_message")
    fake.delay = MagicMock(name="delay")
    monkeypatch.setattr(webhook_module, "process_incoming_message", fake)
    return fake


@pytest.mark.asyncio
async def test_get_verify_handshake(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": VERIFY_TOKEN,
            "hub.challenge": "challenge-123",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "challenge-123"


@pytest.mark.asyncio
async def test_post_rejects_invalid_signature(
    client: AsyncClient, patched_dispatch: MagicMock
) -> None:
    body = json.dumps(_sample_payload()).encode()
    resp = await client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert resp.status_code == 403
    patched_dispatch.delay.assert_not_called()


@pytest.mark.asyncio
async def test_post_valid_signature_dispatches(
    client: AsyncClient, patched_dispatch: MagicMock
) -> None:
    body = json.dumps(_sample_payload()).encode()
    resp = await client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _sign(body),
            "X-Correlation-Id": "corr-abc",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "received", "queued": 1}
    patched_dispatch.delay.assert_called_once()
    payload_arg, corr_arg = patched_dispatch.delay.call_args.args
    assert payload_arg["meta_message_id"] == "wamid.test.1"
    assert payload_arg["from_phone"] == "+51900000001"
    assert payload_arg["text"] == "Hola, dudas sobre matricula"
    assert corr_arg == "corr-abc"


@pytest.mark.asyncio
async def test_post_ignores_non_text_messages(
    client: AsyncClient, patched_dispatch: MagicMock
) -> None:
    payload = _sample_payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0] = {
        "from": "51900000002",
        "id": "wamid.test.2",
        "timestamp": "1700000000",
        "type": "image",
    }
    body = json.dumps(payload).encode()
    resp = await client.post(
        "/api/webhooks/whatsapp",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": _sign(body),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["queued"] == 0
    patched_dispatch.delay.assert_not_called()


@pytest.mark.asyncio
async def test_worker_idempotent_on_duplicate_meta_id(
    db_session: AsyncSession,
    postgres_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling _process_async twice with the same meta_message_id inserts only one row."""
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    get_settings.cache_clear()

    parsed = ParsedInboundMessage(
        meta_message_id="wamid.dup.1",
        from_phone="+51900000050",
        display_name="Test Dup",
        text="hola",
        timestamp="1700000000",
    ).model_dump()

    # Pre-create student so the welcome path doesn't fire (SW-12 scope).
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from chatbot_api.repositories.student import student_repository

    setup_engine = create_async_engine(postgres_url)
    setup_factory = async_sessionmaker(setup_engine, expire_on_commit=False)
    async with setup_factory() as setup_db:
        await student_repository.upsert_by_phone(setup_db, phone_e164="+51900000050")
        await setup_db.commit()
    await setup_engine.dispose()

    fake_answer = AsyncMock(return_value={"text": "ok", "tool_calls": []})
    fake_send = AsyncMock(return_value="wamid.bot.dup")
    with (
        patch("chatbot_api.workers.conversation.rag_service.answer", fake_answer),
        patch(
            "chatbot_api.workers.conversation.whatsapp_service.send_message", fake_send
        ),
    ):
        await _process_async(parsed, "corr-1")
        await _process_async(parsed, "corr-2")

    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as verify:
        msg_count = (
            await verify.execute(
                select(Message).where(Message.meta_message_id == "wamid.dup.1")
            )
        ).scalars().all()
        students = (
            await verify.execute(
                select(Student).where(Student.phone_e164 == "+51900000050")
            )
        ).scalars().all()
    await engine.dispose()

    assert len(msg_count) == 1
    assert len(students) == 1
