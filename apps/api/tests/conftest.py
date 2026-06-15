import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

API_DIR = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def _disable_history_cache_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """SW-26 cache: off por defecto en tests para evitar leakage cross-run.

    Los tests específicos del cache (test_sw26_*) lo re-activan en su fixture.
    """
    monkeypatch.setenv("HISTORY_CACHE_ENABLED", "false")
    # Debounce off por defecto: la ruta inline reproduce el comportamiento
    # 1-mensaje→1-respuesta que asumen los tests existentes. Los tests del
    # debounce ejercen _run_reply/_drain directamente.
    monkeypatch.setenv("REPLY_DEBOUNCE_ENABLED", "false")
    from chatbot_api.core.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as container:
        url = container.get_connection_url()
        os.environ["DATABASE_URL"] = url

        from chatbot_api.core.settings import get_settings

        get_settings.cache_clear()

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


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client wired to the FastAPI app, sharing the test's db_session.

    Overrides `get_session` so route handlers operate inside the test transaction.
    Data inserted via factories is visible to API requests; the rollback at the
    end of the test cleans it up.
    """
    from chatbot_api.core.db import get_session
    from chatbot_api.main import app

    async def _override_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    try:
        async with LifespanManager(app):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as ac:
                yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)
