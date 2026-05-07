from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.core.db import get_session
from chatbot_api.core.settings import get_settings
from chatbot_api.models import Admin
from chatbot_api.services.admin_service import admin_service


async def get_current_admin(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Admin:
    settings = get_settings()

    if settings.env == "local":
        email = request.headers.get("X-Dev-User")
        if not email:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "missing X-Dev-User header (local env)",
            )
        admin = await admin_service.get_active_by_email(db, email)
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
