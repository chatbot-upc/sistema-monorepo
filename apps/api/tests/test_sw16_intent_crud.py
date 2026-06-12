"""SW-16 (HU07) — CRUD de intenciones + frases de ejemplo."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Intent

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


@pytest.fixture(autouse=True)
def _stub_index_bump(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """No tocar Redis en tests; capturar las invalidaciones de índice."""
    bump = AsyncMock()
    monkeypatch.setattr(
        "chatbot_api.services.intent_service.intent_classifier_service.bump_index_generation",
        bump,
    )
    return bump


async def test_create_intent(
    client: AsyncClient, db_session: AsyncSession, _stub_index_bump: AsyncMock
) -> None:
    response = await client.post(
        "/api/v1/intents",
        json={
            "name": "consulta_horarios",
            "description": "Preguntas sobre horarios de clase",
            "examples": ["a qué hora es mi clase", "horario de cursos"],
        },
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "consulta_horarios"
    assert body["examples"] == ["a qué hora es mi clase", "horario de cursos"]
    assert body["active"] is True
    _stub_index_bump.assert_awaited_once()


async def test_create_intent_duplicate_name_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await factories.make_intent(db_session, name="dup_intent")
    response = await client.post(
        "/api/v1/intents",
        json={"name": "dup_intent", "examples": ["hola"]},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 409


async def test_create_intent_validates_name_and_examples(
    client: AsyncClient,
) -> None:
    # name con mayúsculas / espacios → 422
    r1 = await client.post(
        "/api/v1/intents",
        json={"name": "Mal Nombre", "examples": ["x"]},
        headers=DEV_USER_HEADER,
    )
    assert r1.status_code == 422
    # examples vacío → 422
    r2 = await client.post(
        "/api/v1/intents",
        json={"name": "valido", "examples": []},
        headers=DEV_USER_HEADER,
    )
    assert r2.status_code == 422


async def test_update_intent_examples(
    client: AsyncClient, db_session: AsyncSession, _stub_index_bump: AsyncMock
) -> None:
    intent = await factories.make_intent(db_session, name="upd_intent")
    response = await client.put(
        f"/api/v1/intents/{intent.id}",
        json={"examples": ["nuevo ejemplo 1", "nuevo ejemplo 2"], "active": False},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["examples"] == ["nuevo ejemplo 1", "nuevo ejemplo 2"]
    assert body["active"] is False
    _stub_index_bump.assert_awaited_once()


async def test_update_intent_does_not_change_name(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """El name es inmutable: aunque se mande en el body, no cambia."""
    intent = await factories.make_intent(db_session, name="immutable_name")
    # IntentUpdate no tiene campo name → se ignora si se manda
    response = await client.put(
        f"/api/v1/intents/{intent.id}",
        json={"name": "otro_nombre", "examples": ["x"]},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "immutable_name"


async def test_update_intent_404(client: AsyncClient) -> None:
    response = await client.put(
        "/api/v1/intents/999999",
        json={"active": False},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 404


async def test_delete_intent(
    client: AsyncClient, db_session: AsyncSession, _stub_index_bump: AsyncMock
) -> None:
    intent = await factories.make_intent(db_session, name="del_intent")
    intent_id = intent.id
    response = await client.delete(
        f"/api/v1/intents/{intent_id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 204
    _stub_index_bump.assert_awaited_once()

    rows = (
        await db_session.execute(select(Intent).where(Intent.id == intent_id))
    ).scalars().all()
    assert len(rows) == 0


async def test_delete_intent_404(client: AsyncClient) -> None:
    response = await client.delete(
        "/api/v1/intents/999999", headers=DEV_USER_HEADER
    )
    assert response.status_code == 404
