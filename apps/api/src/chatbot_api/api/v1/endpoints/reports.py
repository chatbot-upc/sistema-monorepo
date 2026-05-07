from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
async def dashboard(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    return await report_service.get_dashboard_stats(db)


@router.get("/conversations")
async def conversations_by_day(
    from_date: date = Query(..., alias="from_date"),
    to_date: date = Query(..., alias="to_date"),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await report_service.get_conversations_by_day(
        db, from_date=from_date, to_date=to_date
    )


@router.get("/intents")
async def intents_distribution(
    from_date: date = Query(..., alias="from_date"),
    to_date: date = Query(..., alias="to_date"),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await report_service.get_intent_distribution(
        db, from_date=from_date, to_date=to_date
    )
