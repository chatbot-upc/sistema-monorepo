from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.api.dependencies import get_current_admin
from chatbot_api.core.db import get_session
from chatbot_api.models import Admin
from chatbot_api.schemas.admin_device import DeviceRead, DeviceRegisterRequest
from chatbot_api.services import push_service

router = APIRouter(prefix="/admin/devices", tags=["admin-devices"])


@router.post(
    "",
    response_model=DeviceRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    req: DeviceRegisterRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_session),
) -> DeviceRead:
    device = await push_service.register_device(
        db,
        admin_id=admin.id,
        fcm_token=req.fcm_token,
        platform=req.platform,
        user_agent=req.user_agent,
    )
    await db.commit()
    return DeviceRead.model_validate(device)
