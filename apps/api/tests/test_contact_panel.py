"""Ficha de contacto: correo, destacar, etiquetas, notas e historial."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models.enums import ConversationStatus, MessageRole

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


async def test_update_contact_email(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51955000001")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )

    r = await client.patch(
        f"/api/v1/conversations/{conv.id}/contact",
        headers=DEV_USER_HEADER,
        json={"email": "alumno@upc.edu.pe"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "alumno@upc.edu.pe"

    # Vaciar el correo lo deja en null.
    r2 = await client.patch(
        f"/api/v1/conversations/{conv.id}/contact",
        headers=DEV_USER_HEADER,
        json={"email": "  "},
    )
    assert r2.status_code == 200
    assert r2.json()["email"] is None


async def test_star_toggle(client: AsyncClient, db_session: AsyncSession) -> None:
    student = await factories.make_student(db_session, phone="+51955000002")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )

    r = await client.put(
        f"/api/v1/conversations/{conv.id}/star",
        headers=DEV_USER_HEADER,
        json={"starred": True},
    )
    assert r.status_code == 200
    assert r.json()["starred"] is True


async def test_tag_catalog_and_assignment(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51955000003")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )

    created = await client.post(
        "/api/v1/tags",
        headers=DEV_USER_HEADER,
        json={"name": "deuda", "color": "amber"},
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]

    # Nombre duplicado → 409.
    dup = await client.post(
        "/api/v1/tags",
        headers=DEV_USER_HEADER,
        json={"name": "deuda", "color": "blue"},
    )
    assert dup.status_code == 409

    assigned = await client.post(
        f"/api/v1/conversations/{conv.id}/tags",
        headers=DEV_USER_HEADER,
        json={"tag_id": tag_id},
    )
    assert assigned.status_code == 200
    assert [t["name"] for t in assigned.json()["tags"]] == ["deuda"]

    removed = await client.delete(
        f"/api/v1/conversations/{conv.id}/tags/{tag_id}",
        headers=DEV_USER_HEADER,
    )
    assert removed.status_code == 200
    assert removed.json()["tags"] == []


async def test_notes_crud(client: AsyncClient, db_session: AsyncSession) -> None:
    student = await factories.make_student(db_session, phone="+51955000004")
    conv = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )

    created = await client.post(
        f"/api/v1/conversations/{conv.id}/notes",
        headers=DEV_USER_HEADER,
        json={"body": "Derivar a Tesorería"},
    )
    assert created.status_code == 201
    note_id = created.json()["id"]
    assert created.json()["author_name"] is not None

    listed = await client.get(
        f"/api/v1/conversations/{conv.id}/notes", headers=DEV_USER_HEADER
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    edited = await client.patch(
        f"/api/v1/conversations/{conv.id}/notes/{note_id}",
        headers=DEV_USER_HEADER,
        json={"body": "Ya pagó, continuar matrícula"},
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Ya pagó, continuar matrícula"

    deleted = await client.delete(
        f"/api/v1/conversations/{conv.id}/notes/{note_id}",
        headers=DEV_USER_HEADER,
    )
    assert deleted.status_code == 204

    empty = await client.get(
        f"/api/v1/conversations/{conv.id}/notes", headers=DEV_USER_HEADER
    )
    assert empty.json() == []


async def test_history_aggregates_by_phone(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    student = await factories.make_student(db_session, phone="+51955000005")
    conv1 = await factories.make_conversation(
        db_session,
        student_phone=student.phone_e164,
        status=ConversationStatus.cerrada,
    )
    conv2 = await factories.make_conversation(
        db_session, student_phone=student.phone_e164
    )
    await factories.make_message(
        db_session, conversation_id=conv1.id, role=MessageRole.student, content="hola"
    )
    await factories.make_message(
        db_session, conversation_id=conv2.id, role=MessageRole.bot, content="hola!"
    )

    r = await client.get(
        f"/api/v1/conversations/{conv2.id}/history", headers=DEV_USER_HEADER
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_conversations"] == 2
    assert body["total_messages"] == 2
