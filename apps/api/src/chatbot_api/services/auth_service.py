"""Auth service — bridge to AWS Cognito via boto3."""

from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status

from chatbot_api.core.settings import get_settings

_client: Any | None = None


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
