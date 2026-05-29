from collections.abc import Sequence

from pydantic import BaseModel
from sqlalchemy import delete, select
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

    async def delete_many(
        self, db: AsyncSession, device_ids: Sequence[int]
    ) -> int:
        """Bulk-delete device rows (used to evict dead FCM tokens). Returns
        the row count actually removed."""
        if not device_ids:
            return 0
        result = await db.execute(
            delete(AdminDevice).where(AdminDevice.id.in_(device_ids))
        )
        return int(getattr(result, "rowcount", 0) or 0)


admin_device_repository = AdminDeviceRepository(AdminDevice)
