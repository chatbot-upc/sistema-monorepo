"""FastAPI dependencies — auth + DB session."""

import re

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.db import get_session
from chatbot_api.core.security import decode_id_token
from chatbot_api.core.settings import get_settings
from chatbot_api.models import Admin
from chatbot_api.repositories.admin import admin_repository

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_bearer = HTTPBearer(auto_error=False)


async def get_current_admin(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_session),
) -> Admin:
    """Resolve current admin from JWT (Authorization Bearer) or X-Dev-User stub.

    Priority:
    1. Authorization Bearer ID token → validate against Cognito JWKs
    2. ENV=local + X-Dev-User header → stub for tests/dev
    3. Else → 401
    """
    settings = get_settings()

    if creds is not None:
        claims = await decode_id_token(creds.credentials)
        email = claims.get("email")
        if not email:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "token_missing_email"
            )
        admin = await admin_repository.get_active_by_email(db, email.lower())
        if admin is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"admin '{email}' not found or inactive",
            )
        return admin

    if settings.env == "local":
        raw = request.headers.get("X-Dev-User")
        email_raw = raw.strip().lower() if raw else None
        if email_raw and _EMAIL_RE.match(email_raw):
            admin = await admin_repository.get_active_by_email(db, email_raw)
            if admin is None:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    f"admin '{email_raw}' not found or inactive",
                )
            return admin
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "missing or malformed X-Dev-User header (expected email)",
        )

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED, "missing_authorization_token"
    )
