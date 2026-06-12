"""SW-54 (HU46) — versionado del prompt del agente."""

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.repositories.prompt_version import prompt_version_repository

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}

_SAMPLE = "Este es un prompt de prueba con suficiente longitud para pasar."


@pytest.fixture(autouse=True)
def _stub_prompt_bump(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """No tocar Redis; capturar invalidaciones de generación."""
    bump = AsyncMock()
    monkeypatch.setattr(
        "chatbot_api.services.prompt_service.rag_service.bump_prompt_generation",
        bump,
    )
    return bump


async def _seed_v1(db: AsyncSession) -> None:
    """La migración 0009 siembra v1 en prod, pero el testcontainer parte limpio
    salvo lo que migra. v1 ya existe vía migración; este helper no hace nada
    si ya está."""
    existing = await prompt_version_repository.get_active(db, "agent_system")
    if existing is None:
        from chatbot_api.models import PromptVersion

        db.add(
            PromptVersion(
                name="agent_system",
                version=1,
                content="Prompt base sembrado para el test, largo suficiente.",
                active=True,
            )
        )
        await db.flush()


async def test_list_versions_includes_active(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_v1(db_session)
    response = await client.get("/api/v1/prompts", headers=DEV_USER_HEADER)
    assert response.status_code == 200
    body = response.json()
    assert any(v["active"] for v in body)
    assert all(v["name"] == "agent_system" for v in body)


async def test_create_version_increments(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_v1(db_session)
    before = await client.get("/api/v1/prompts", headers=DEV_USER_HEADER)
    max_before = max(v["version"] for v in before.json())

    response = await client.post(
        "/api/v1/prompts",
        json={"content": _SAMPLE},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == max_before + 1
    assert body["active"] is False


async def test_create_validates_min_length(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/prompts",
        json={"content": "corto"},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 422


async def test_activate_deactivates_others(
    client: AsyncClient, db_session: AsyncSession, _stub_prompt_bump: AsyncMock
) -> None:
    await _seed_v1(db_session)
    created = await client.post(
        "/api/v1/prompts",
        json={"content": _SAMPLE},
        headers=DEV_USER_HEADER,
    )
    new_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/prompts/{new_id}/activate", headers=DEV_USER_HEADER
    )
    assert response.status_code == 200
    assert response.json()["active"] is True
    _stub_prompt_bump.assert_awaited()

    # Solo una activa
    listing = await client.get("/api/v1/prompts", headers=DEV_USER_HEADER)
    actives = [v for v in listing.json() if v["active"]]
    assert len(actives) == 1
    assert actives[0]["id"] == new_id


async def test_update_version_content(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_v1(db_session)
    created = await client.post(
        "/api/v1/prompts",
        json={"content": _SAMPLE},
        headers=DEV_USER_HEADER,
    )
    new_id = created.json()["id"]

    updated = "Contenido editado del prompt, también con longitud válida."
    response = await client.put(
        f"/api/v1/prompts/{new_id}",
        json={"content": updated},
        headers=DEV_USER_HEADER,
    )
    assert response.status_code == 200
    assert response.json()["content"] == updated


async def test_delete_active_blocked_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_v1(db_session)
    listing = await client.get("/api/v1/prompts", headers=DEV_USER_HEADER)
    active_id = next(v["id"] for v in listing.json() if v["active"])

    response = await client.delete(
        f"/api/v1/prompts/{active_id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 409


async def test_delete_inactive_ok(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _seed_v1(db_session)
    created = await client.post(
        "/api/v1/prompts",
        json={"content": _SAMPLE},
        headers=DEV_USER_HEADER,
    )
    new_id = created.json()["id"]
    response = await client.delete(
        f"/api/v1/prompts/{new_id}", headers=DEV_USER_HEADER
    )
    assert response.status_code == 204


async def test_get_active_returns_activated_content(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """rag_service debe poder resolver la versión activa desde la DB."""
    await _seed_v1(db_session)
    created = await client.post(
        "/api/v1/prompts",
        json={"content": "Prompt v2 activado para verificar get_active."},
        headers=DEV_USER_HEADER,
    )
    new_id = created.json()["id"]
    await client.post(
        f"/api/v1/prompts/{new_id}/activate", headers=DEV_USER_HEADER
    )

    active = await prompt_version_repository.get_active(db_session, "agent_system")
    assert active is not None
    assert active.id == new_id
    assert "v2 activado" in active.content
