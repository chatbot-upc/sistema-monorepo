"""Read endpoints with real DB queries + pagination + filters."""

from datetime import datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import ConversationStatus, DocumentStatus, MessageRole

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


async def test_list_conversations_paginated(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900100001")
    for _ in range(5):
        await factories.make_conversation(db_session, student_phone=student.phone_e164)

    response = await client.get(
        "/api/v1/conversations?page=1&size=2", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 5
    assert body["pages"] == 3


async def test_list_conversations_filter_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900100002")
    await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.abierta
    )
    await factories.make_conversation(
        db_session, student_phone=student.phone_e164, status=ConversationStatus.cerrada
    )

    response = await client.get(
        "/api/v1/conversations?status=cerrada", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "cerrada" for item in body["items"])


async def test_get_conversation_detail_includes_messages(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900100003")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    await factories.make_message(
        db_session, conversation_id=conv.id, role=MessageRole.student, content="hola"
    )
    await factories.make_message(
        db_session, conversation_id=conv.id, role=MessageRole.bot, content="hola back"
    )

    response = await client.get(
        f"/api/v1/conversations/{conv.id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["messages"]) == 2


async def test_get_conversation_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/conversations/999999", headers=DEV_USER_HEADER)
    assert response.status_code == 404


async def test_get_document_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/documents/999999", headers=DEV_USER_HEADER)
    assert response.status_code == 404


async def test_get_intent_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/intents/999999", headers=DEV_USER_HEADER)
    assert response.status_code == 404


async def test_list_messages_paginated(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51900100004")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    for i in range(7):
        await factories.make_message(
            db_session, conversation_id=conv.id, content=f"msg{i}"
        )

    response = await client.get(
        f"/api/v1/conversations/{conv.id}/messages?size=3", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 3
    assert body["total"] == 7


async def test_list_documents_filter_status(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await factories.make_document(
        db_session, sha256="b" * 64, status=DocumentStatus.indexed
    )
    await factories.make_document(
        db_session, sha256="c" * 64, status=DocumentStatus.pending
    )

    response = await client.get(
        "/api/v1/documents?status=indexed", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert all(item["status"] == "indexed" for item in body["items"])


async def test_list_intents_active_only(client: AsyncClient) -> None:
    """Migración 0003 deja 3 intents activos seedeados."""
    response = await client.get(
        "/api/v1/intents?active=true", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    seed_names = {"consulta_fechas", "consulta_costos", "consulta_becas"}
    returned_names = {item["name"] for item in body["items"]}
    assert seed_names <= returned_names


async def test_list_notifications_empty(client: AsyncClient) -> None:
    response = await client.get("/api/v1/notifications", headers=DEV_USER_HEADER)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_dashboard_stats(client: AsyncClient, db_session: AsyncSession) -> None:
    student = await factories.make_student(db_session, phone="+51900100005")
    await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.abierta,
    )
    await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.takeover,
    )
    await factories.make_document(
        db_session, sha256="d" * 64, status=DocumentStatus.indexed
    )

    response = await client.get(
        "/api/v1/reports/dashboard", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert body["conversations_open"] >= 1
    assert body["conversations_active"] >= 1
    assert body["conversations_escalated"] >= 1
    assert body["documents_indexed"] >= 1
    assert body["intents_active"] >= 3  # seed
    # Campos KPI nuevos presentes (pueden ser 0/None sin actividad de intents)
    assert "top_intent" in body
    assert "avg_confidence" in body
    assert "avg_latency_ms" in body


async def test_dashboard_top_intent_and_confidence(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Con ConversationIntent sembrado hoy, top_intent y certeza se calculan."""
    from chatbot_api.models import ConversationIntent

    student = await factories.make_student(db_session, phone="+51900100050")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    intent = await factories.make_intent(db_session, name="kpi_test_intent")
    db_session.add(
        ConversationIntent(
            conversation_id=conv.id,
            intent_id=intent.id,
            confidence=0.9,
        )
    )
    await db_session.flush()

    response = await client.get(
        "/api/v1/reports/dashboard", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    body = response.json()
    assert body["top_intent"] is not None
    assert body["top_intent"]["count"] >= 1
    assert body["avg_confidence"] > 0


async def test_reports_conversations_by_day(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    today = datetime.now()
    student = await factories.make_student(db_session, phone="+51900100006")
    await factories.make_conversation(
        db_session, student_phone=student.phone_e164, opened_at=today
    )
    from_date = (today - timedelta(days=1)).date().isoformat()
    to_date = (today + timedelta(days=1)).date().isoformat()

    response = await client.get(
        f"/api/v1/reports/conversations?from_date={from_date}&to_date={to_date}",
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert any(row["count"] >= 1 for row in body)
