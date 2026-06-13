"""SW-39 — takeover / release / close / reopen."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


@pytest.fixture(autouse=True)
def _silence_events(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(event_type: str, data: dict) -> None:
        return None

    from chatbot_api.core import events
    from chatbot_api.services import conversation_service

    monkeypatch.setattr(events, "publish_event", _noop)
    monkeypatch.setattr(conversation_service, "publish_event", _noop)


async def test_takeover_abierta_to_takeover(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300001")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )

    response = await client.post(
        f"/api/v1/conversations/{conv.id}/takeover", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    assert response.json()["status"] == "takeover"
    await db_session.refresh(conv)
    assert conv.status == ConversationStatus.takeover
    assert conv.takeover_admin is not None


async def test_takeover_idempotent_same_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300002")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )

    r1 = await client.post(
        f"/api/v1/conversations/{conv.id}/takeover", headers=DEV_USER_HEADER
    )
    assert r1.status_code == 200
    r2 = await client.post(
        f"/api/v1/conversations/{conv.id}/takeover", headers=DEV_USER_HEADER
    )
    assert r2.status_code == 200


async def test_takeover_rejects_cerrada(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300003")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.cerrada
    )
    response = await client.post(
        f"/api/v1/conversations/{conv.id}/takeover", headers=DEV_USER_HEADER
    )
    assert response.status_code == 409


async def test_release_returns_to_abierta(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300004")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.takeover
    )

    response = await client.post(
        f"/api/v1/conversations/{conv.id}/release", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    await db_session.refresh(conv)
    assert conv.status == ConversationStatus.abierta
    assert conv.takeover_admin is None


async def test_release_rejects_abierta(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300005")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )
    response = await client.post(
        f"/api/v1/conversations/{conv.id}/release", headers=DEV_USER_HEADER
    )
    assert response.status_code == 409


async def test_close_and_reopen_cycle(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300006")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )

    r_close = await client.post(
        f"/api/v1/conversations/{conv.id}/close", headers=DEV_USER_HEADER
    )
    assert r_close.status_code == 200
    await db_session.refresh(conv)
    assert conv.status == ConversationStatus.cerrada
    assert conv.closed_at is not None
    assert conv.closed_by is not None

    r_reopen = await client.post(
        f"/api/v1/conversations/{conv.id}/reopen", headers=DEV_USER_HEADER
    )
    assert r_reopen.status_code == 200
    await db_session.refresh(conv)
    assert conv.status == ConversationStatus.abierta
    assert conv.closed_at is None
    assert conv.closed_by is None


async def test_close_rejects_already_cerrada(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300007")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.cerrada
    )
    response = await client.post(
        f"/api/v1/conversations/{conv.id}/close", headers=DEV_USER_HEADER
    )
    assert response.status_code == 409


async def test_reopen_rejects_abierta(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900300008")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )
    response = await client.post(
        f"/api/v1/conversations/{conv.id}/reopen", headers=DEV_USER_HEADER
    )
    assert response.status_code == 409


async def test_delete_conversation(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from chatbot_api.models import Conversation

    student = await factories.make_student(db_session, phone="+51900300009")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    await factories.make_message(db_session, conversation_id=conv.id, content="hola")
    conv_id = conv.id

    response = await client.delete(
        f"/api/v1/conversations/{conv_id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 204

    rows = (
        await db_session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
    ).scalars().all()
    assert len(rows) == 0


async def test_delete_conversation_404(client: AsyncClient) -> None:
    response = await client.delete(
        "/api/v1/conversations/999999", headers=DEV_USER_HEADER
    )
    assert response.status_code == 404
