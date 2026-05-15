from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.monitoring import MonitoringHealth
from chatbot_api.services import monitoring_service

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health", response_model=MonitoringHealth)
async def monitoring_health(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> MonitoringHealth:
    return await monitoring_service.get_health(db)
