"""Auth service — bridge to AWS Cognito via boto3."""

import secrets
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from chatbot_api.core.settings import get_settings

_client: Any | None = None

_WS_TICKET_TTL_SECONDS = 60
_WS_TICKET_PREFIX = "chatbot:ws-ticket:"


def _get_client() -> Any:
    global _client
    if _client is None:
        settings = get_settings()
        _client = boto3.client("cognito-idp", region_name=settings.cognito_region)
    return _client


def reset_client() -> None:
    """Test helper — reset cached boto3 client."""
    global _client
    _client = None


async def login(*, email: str, password: str) -> dict[str, Any]:
    """Login via Cognito USER_PASSWORD_AUTH. Returns dict with access/id/refresh tokens."""
    settings = get_settings()
    client = _get_client()
    try:
        resp = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        if code in {"NotAuthorizedException", "UserNotFoundException"}:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "invalid_credentials"
            ) from exc
        if code == "UserNotConfirmedException":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "user_not_confirmed"
            ) from exc
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"cognito_error: {code}"
        ) from exc

    auth = resp.get("AuthenticationResult")
    if auth is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "auth_challenge_required"
        )
    return {
        "access_token": auth["AccessToken"],
        "id_token": auth["IdToken"],
        "refresh_token": auth["RefreshToken"],
        "expires_in": auth["ExpiresIn"],
    }


async def refresh(*, refresh_token: str) -> dict[str, Any]:
    """Refresh tokens via REFRESH_TOKEN_AUTH."""
    settings = get_settings()
    client = _get_client()
    try:
        resp = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
        )
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        if code == "NotAuthorizedException":
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token"
            ) from exc
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, f"cognito_error: {code}"
        ) from exc

    auth = resp.get("AuthenticationResult")
    if auth is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh_failed")
    return {
        "access_token": auth["AccessToken"],
        "id_token": auth["IdToken"],
        "expires_in": auth["ExpiresIn"],
    }


async def issue_ws_ticket(admin_id: int) -> dict[str, Any]:
    """One-shot ticket for the WebSocket handshake (SW-36/37 realtime).

    Browsers can't set Authorization headers on `new WebSocket(...)`, so we
    trade the admin's Bearer JWT for a short-lived opaque ticket they put on
    the WS query string. The ticket lives in Redis with a 60s TTL and is
    consumed (deleted) on first use to defeat replay.
    """
    settings = get_settings()
    ticket = secrets.token_urlsafe(24)
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url)
    try:
        await client.set(
            f"{_WS_TICKET_PREFIX}{ticket}",
            str(admin_id),
            ex=_WS_TICKET_TTL_SECONDS,
        )
    finally:
        await client.aclose()
    return {"ticket": ticket, "expires_in": _WS_TICKET_TTL_SECONDS}


async def consume_ws_ticket(ticket: str) -> int | None:
    """Atomically read+delete a ticket. Returns admin_id or None if invalid."""
    if not ticket:
        return None
    settings = get_settings()
    from redis.asyncio import Redis

    client = Redis.from_url(settings.redis_url)
    try:
        key = f"{_WS_TICKET_PREFIX}{ticket}"
        # GETDEL is atomic — no race where two clients consume the same ticket.
        raw = await client.getdel(key)
    finally:
        await client.aclose()
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
