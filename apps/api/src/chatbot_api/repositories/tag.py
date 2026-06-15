from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot_api.models import Tag


class TagRepository:
    async def list_all(self, db: AsyncSession) -> list[Tag]:
        result = await db.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, tag_id: int) -> Tag | None:
        result = await db.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalars().first()

    async def get_by_name(self, db: AsyncSession, name: str) -> Tag | None:
        result = await db.execute(select(Tag).where(Tag.name == name))
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, name: str, color: str) -> Tag:
        tag = Tag(name=name, color=color)
        db.add(tag)
        await db.flush()
        await db.refresh(tag)
        return tag


tag_repository = TagRepository()
