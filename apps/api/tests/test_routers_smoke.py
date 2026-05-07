"""Smoke tests: auth + correlation + webhook."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import AdminRole

from . import factories

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


async def test_unauth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 401


async def test_unknown_admin_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/conversations", headers={"X-Dev-User": "ghost@x.com"}
    )
    assert response.status_code == 401


async def test_malformed_email_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/conversations", headers={"X-Dev-User": "not-an-email"}
    )
    assert response.status_code == 401
    assert "malformed" in response.json()["detail"].lower()


async def test_inactive_admin_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await factories.make_admin(
        db_session,
        email="inactive@upc.edu.pe",
        name="Inactive",
        role=AdminRole.admin,
        active=False,
    )
    response = await client.get(
        "/api/v1/conversations", headers={"X-Dev-User": "inactive@upc.edu.pe"}
    )
    assert response.status_code == 401


async def test_auth_me_returns_admin(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me", headers=DEV_USER_HEADER)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "dev@upc.edu.pe"
    assert body["role"] == "admin"


async def test_correlation_id_generated(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert "X-Correlation-Id" in response.headers
    assert len(response.headers["X-Correlation-Id"]) > 0


async def test_correlation_id_propagated(client: AsyncClient) -> None:
    response = await client.get(
        "/health", headers={"X-Correlation-Id": "test-123-abc"}
    )
    assert response.headers["X-Correlation-Id"] == "test-123-abc"


async def test_webhook_verify_no_token_configured(client: AsyncClient) -> None:
    response = await client.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "any",
            "hub.challenge": "hello",
        },
    )
    assert response.status_code == 403


async def test_webhook_verify_handshake_ok(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chatbot_api.core.settings import get_settings

    monkeypatch.setenv("META_VERIFY_TOKEN", "test-secret")
    get_settings.cache_clear()
    try:
        response = await client.get(
            "/api/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-secret",
                "hub.challenge": "challenge-123",
            },
        )
        assert response.status_code == 200
        assert response.text == "challenge-123"
    finally:
        get_settings.cache_clear()


async def test_webhook_verify_wrong_token(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from chatbot_api.core.settings import get_settings

    monkeypatch.setenv("META_VERIFY_TOKEN", "test-secret")
    get_settings.cache_clear()
    try:
        response = await client.get(
            "/api/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "WRONG",
                "hub.challenge": "abc",
            },
        )
        assert response.status_code == 403
    finally:
        get_settings.cache_clear()


async def test_webhook_post_returns_200(client: AsyncClient) -> None:
    response = await client.post(
        "/api/webhooks/whatsapp", json={"object": "whatsapp_business_account"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"


async def test_takeover_not_implemented(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversations/1/takeover", headers=DEV_USER_HEADER
    )
    assert response.status_code == 501


async def test_upload_document_requires_file(client: AsyncClient) -> None:
    """POST /documents está implementado (Fase 3) — sin file devuelve 422."""
    response = await client.post("/api/v1/documents", headers=DEV_USER_HEADER)
    assert response.status_code == 422


async def test_create_intent_not_implemented(client: AsyncClient) -> None:
    response = await client.post("/api/v1/intents", headers=DEV_USER_HEADER)
    assert response.status_code == 501
