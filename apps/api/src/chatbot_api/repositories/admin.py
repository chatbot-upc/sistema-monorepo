from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Admin

from .base import BaseRepository


class _AdminCreate(BaseModel):
    pass


class _AdminUpdate(BaseModel):
    pass


class AdminRepository(BaseRepository[Admin, _AdminCreate, _AdminUpdate]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Admin | None:
        result = await db.execute(select(Admin).where(Admin.email == email))
        return result.scalars().first()

    async def get_active_by_email(self, db: AsyncSession, email: str) -> Admin | None:
        result = await db.execute(
            select(Admin).where(Admin.email == email, Admin.active.is_(True))
        )
        return result.scalars().first()


admin_repository = AdminRepository(Admin)
