import re

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.db import get_session
from chatbot_api.core.settings import get_settings
from chatbot_api.models import Admin
from chatbot_api.repositories.admin import admin_repository

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Admin:
    settings = get_settings()

    if settings.env == "local":
        raw = request.headers.get("X-Dev-User")
        email = raw.strip().lower() if raw else None
        if not email or not _EMAIL_RE.match(email):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "missing or malformed X-Dev-User header (expected email)",
            )
        admin = await admin_repository.get_active_by_email(db, email)
        if admin is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                f"admin '{email}' not found or inactive",
            )
        return admin

    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "Cognito JWT validation not implemented yet (Fase 5)",
    )
