from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import AdminDevice

from .base import BaseRepository


class _DeviceCreate(BaseModel):
    pass


class _DeviceUpdate(BaseModel):
    pass


class AdminDeviceRepository(
    BaseRepository[AdminDevice, _DeviceCreate, _DeviceUpdate]
):
    async def get_by_token(
        self, db: AsyncSession, fcm_token: str
    ) -> AdminDevice | None:
        result = await db.execute(
            select(AdminDevice).where(AdminDevice.fcm_token == fcm_token)
        )
        return result.scalars().first()

    async def list_by_admin(
        self, db: AsyncSession, admin_id: int
    ) -> list[AdminDevice]:
        result = await db.execute(
            select(AdminDevice).where(AdminDevice.admin_id == admin_id)
        )
        return list(result.scalars().all())


admin_device_repository = AdminDeviceRepository(AdminDevice)
