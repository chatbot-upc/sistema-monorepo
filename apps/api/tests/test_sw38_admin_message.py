"""SW-38 — admin envía mensajes al estudiante desde el CRM."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Message
from chatbot_api.models.enums import ConversationStatus, MessageRole

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


@pytest.fixture(autouse=True)
def _stub_outbound(monkeypatch: pytest.MonkeyPatch) -> None:
    """No reuses Meta Cloud API ni Redis en tests unitarios."""
    from chatbot_api.services import whatsapp_service

    async def _fake_send(*, to: str, body: str) -> str:
        return f"wamid.test.{to[-4:]}"

    monkeypatch.setattr(whatsapp_service, "send_message", _fake_send)

    from chatbot_api.core import events

    async def _noop(event_type: str, data: dict) -> None:
        return None

    monkeypatch.setattr(events, "publish_event", _noop)
    from chatbot_api.services import conversation_service

    monkeypatch.setattr(conversation_service, "publish_event", _noop)


async def test_send_admin_message_persists_with_role_and_admin_id(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900200001")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.takeover
    )
    # dev@upc.edu.pe gets auto-provisioned as admin by the dev header.
    response = await client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"body": "Hola, soy un asesor humano"},
        headers=DEV_USER_HEADER,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["meta_message_id"].startswith("wamid.test.")
    assert body["conversation_status"] == "takeover"

    rows = (
        await db_session.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
    ).scalars().all()
    assert len(rows) == 1
    msg = rows[0]
    assert msg.role == MessageRole.admin
    assert msg.admin_id is not None
    assert msg.content == "Hola, soy un asesor humano"
    assert msg.meta_message_id == body["meta_message_id"]


async def test_send_admin_message_auto_takeover_on_abierta(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900200002")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )

    response = await client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"body": "Te respondo yo"},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 201
    assert response.json()["conversation_status"] == "takeover"

    await db_session.refresh(conv)
    assert conv.status == ConversationStatus.takeover
    assert conv.takeover_admin is not None


async def test_send_admin_message_rejects_cerrada(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900200003")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.cerrada
    )

    response = await client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"body": "intento tarde"},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 409


async def test_send_admin_message_validates_body(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900200004")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )

    response = await client.post(
        f"/api/v1/conversations/{conv.id}/messages",
        json={"body": ""},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 422


async def test_send_admin_message_404(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversations/999999/messages",
        json={"body": "hola"},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 404
