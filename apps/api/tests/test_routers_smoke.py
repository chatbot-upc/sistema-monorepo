"""Smoke tests: auth + correlation + webhook (no DB queries needed)."""

from httpx import AsyncClient

DEV_USER_HEADER = {"X-Dev-User": "dev@upc.edu.pe"}


async def test_unauth_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/conversations")
    assert response.status_code == 401


async def test_unknown_admin_returns_401(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/conversations", headers={"X-Dev-User": "ghost@x.com"}
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
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "any",
            "hub.challenge": "hello",
        },
    )
    assert response.status_code == 403


async def test_webhook_post_returns_200(client: AsyncClient) -> None:
    response = await client.post(
        "/webhooks/whatsapp", json={"object": "whatsapp_business_account"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "received"


async def test_takeover_not_implemented(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/conversations/1/takeover", headers=DEV_USER_HEADER
    )
    assert response.status_code == 501


async def test_upload_document_not_implemented(client: AsyncClient) -> None:
    response = await client.post("/api/v1/documents", headers=DEV_USER_HEADER)
    assert response.status_code == 501


async def test_create_intent_not_implemented(client: AsyncClient) -> None:
    response = await client.post("/api/v1/intents", headers=DEV_USER_HEADER)
    assert response.status_code == 501
