"""Acuses de entrega de salientes (sent/delivered/read) desde webhooks de Meta."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.settings import get_settings
from chatbot_api.models import Message
from chatbot_api.models.enums import MessageRole
from chatbot_api.repositories.message import (
    _should_advance_delivery,
    message_repository,
)
from chatbot_api.schemas.whatsapp import WhatsAppWebhookPayload
from chatbot_api.services.whatsapp_webhook_service import extract_statuses

from . import factories


def test_extract_statuses_parses() -> None:
    payload = WhatsAppWebhookPayload.model_validate(
        {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {"id": "wamid.out.1", "status": "delivered"},
                                    {"id": "wamid.out.2", "status": "read"},
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    )
    sts = extract_statuses(payload)
    assert [(s.meta_message_id, s.status) for s in sts] == [
        ("wamid.out.1", "delivered"),
        ("wamid.out.2", "read"),
    ]


def test_should_advance_delivery_is_monotonic() -> None:
    assert _should_advance_delivery(None, "sent")
    assert _should_advance_delivery("sent", "delivered")
    assert _should_advance_delivery("delivered", "read")
    # No retrocede.
    assert not _should_advance_delivery("read", "delivered")
    assert not _should_advance_delivery("read", "sent")
    # failed solo aplica si aún no fue entregado/leído.
    assert _should_advance_delivery("sent", "failed")
    assert not _should_advance_delivery("read", "failed")


async def test_update_delivery_status_advances_and_no_downgrade(
    db_session: AsyncSession,
) -> None:
    student = await factories.make_student(db_session, phone="+51900500001")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    m = Message(
        conversation_id=conv.id,
        role=MessageRole.bot,
        content="hola",
        retrieved_chunks=[],
        meta_message_id="wamid.out.x",
        delivery_status="sent",
    )
    db_session.add(m)
    await db_session.flush()

    updated = await message_repository.update_delivery_status(
        db_session, "wamid.out.x", "read"
    )
    assert updated is not None and updated.delivery_status == "read"

    # Un acuse "delivered" tardío no debe retroceder el estado.
    again = await message_repository.update_delivery_status(
        db_session, "wamid.out.x", "delivered"
    )
    assert again is None
    assert m.delivery_status == "read"


async def test_webhook_status_updates_outbound_message(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENV", "local")
    monkeypatch.setenv("META_APP_SECRET", "")
    get_settings.cache_clear()

    student = await factories.make_student(db_session, phone="+51900500002")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    m = Message(
        conversation_id=conv.id,
        role=MessageRole.bot,
        content="hola",
        retrieved_chunks=[],
        meta_message_id="wamid.web.1",
        delivery_status="sent",
    )
    db_session.add(m)
    await db_session.flush()

    from chatbot_api.api import webhooks as wh

    async def _noop(*a: object, **k: object) -> None:
        return None

    monkeypatch.setattr(wh, "publish_event", _noop)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {"id": "wamid.web.1", "status": "read"}
                            ]
                        }
                    }
                ]
            }
        ],
    }
    resp = await client.post(
        "/api/webhooks/whatsapp",
        content=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "received"

    await db_session.refresh(m)
    assert m.delivery_status == "read"
