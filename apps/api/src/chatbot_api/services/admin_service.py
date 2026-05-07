from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Admin
from chatbot_api.repositories.admin import admin_repository
from chatbot_api.schemas.admin import AdminRead


class AdminService:
    def __init__(self) -> None:
        self.repository = admin_repository

    async def get_active_by_email(self, db: AsyncSession, email: str) -> Admin | None:
        return await self.repository.get_active_by_email(db, email)

    async def to_read(self, admin: Admin) -> AdminRead:
        return AdminRead.model_validate(admin)


admin_service = AdminService()
