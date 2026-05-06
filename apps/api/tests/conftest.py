import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

API_DIR = Path(__file__).parent.parent


async def _create_extensions(asyncpg_url: str) -> None:
    plain_url = asyncpg_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(plain_url)
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as container:
        url = container.get_connection_url()
        os.environ["DATABASE_URL"] = url

        from chatbot_api.core.settings import get_settings

        get_settings.cache_clear()

        asyncio.run(_create_extensions(url))

        cfg = Config(str(API_DIR / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", url)
        cfg.set_main_option("script_location", str(API_DIR / "alembic"))
        command.upgrade(cfg, "head")

        yield url


@pytest_asyncio.fixture
async def db_session(postgres_url: str) -> AsyncIterator[AsyncSession]:
    eng = create_async_engine(postgres_url, poolclass=NullPool)
    async with eng.connect() as connection:
        trans = await connection.begin()
        session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await trans.rollback()
    await eng.dispose()
