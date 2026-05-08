"""JWT validation against Cognito JWKs (cached 1h)."""

from time import time
from typing import Any

import httpx
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from chatbot_api.core.settings import get_settings

_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL = 3600.0


async def _get_jwks() -> dict[str, Any]:
    settings = get_settings()
    now = time()
    if _jwks_cache["keys"] is not None and now - _jwks_cache["fetched_at"] < _JWKS_TTL:
        return _jwks_cache["keys"]  # type: ignore[no-any-return]
    url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    _jwks_cache["keys"] = resp.json()
    _jwks_cache["fetched_at"] = now
    return _jwks_cache["keys"]  # type: ignore[no-any-return]


def reset_jwks_cache() -> None:
    """Test helper — clear JWKs cache."""
    _jwks_cache["keys"] = None
    _jwks_cache["fetched_at"] = 0.0


async def decode_id_token(token: str) -> dict[str, Any]:
    """Decode and verify a Cognito ID token.

    ID tokens carry user identity claims (email, name, sub) — used to map to
    the local Admin row. Access tokens don't have email; we use them only as
    bearer for API auth, not for identity.

    Raises HTTPException(401) on validation failure.
    """
    settings = get_settings()
    if not settings.cognito_user_pool_id or not settings.cognito_client_id:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "cognito not configured (user_pool_id/client_id missing)",
        )
    try:
        unverified = jwt.get_unverified_header(token)
        jwks = await _get_jwks()
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified.get("kid")),
            None,
        )
        if key is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "invalid_token: kid_not_found"
            )
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[unverified.get("alg", "RS256")],
            audience=settings.cognito_client_id,
            issuer=(
                f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
                f"{settings.cognito_user_pool_id}"
            ),
        )
    except ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token_expired") from None
    except JWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, f"invalid_token: {exc}"
        ) from exc
    if claims.get("token_use") != "id":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "wrong_token_type: expected id_token",
        )
    return claims
