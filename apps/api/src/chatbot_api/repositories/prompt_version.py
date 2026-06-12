from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import PromptVersion

from .base import BaseRepository


class _PromptCreate(BaseModel):
    pass


class _PromptUpdate(BaseModel):
    pass


class PromptVersionRepository(
    BaseRepository[PromptVersion, _PromptCreate, _PromptUpdate]
):
    async def list_by_name(
        self, db: AsyncSession, name: str
    ) -> list[PromptVersion]:
        result = await db.execute(
            select(PromptVersion)
            .where(PromptVersion.name == name)
            .order_by(PromptVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_active(
        self, db: AsyncSession, name: str
    ) -> PromptVersion | None:
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.name == name,
                PromptVersion.active.is_(True),
            )
        )
        return result.scalars().first()

    async def max_version(self, db: AsyncSession, name: str) -> int:
        result = await db.execute(
            select(func.max(PromptVersion.version)).where(
                PromptVersion.name == name
            )
        )
        return int(result.scalar() or 0)

    async def deactivate_all(self, db: AsyncSession, name: str) -> None:
        await db.execute(
            update(PromptVersion)
            .where(PromptVersion.name == name, PromptVersion.active.is_(True))
            .values(active=False)
        )


prompt_version_repository = PromptVersionRepository(PromptVersion)
