"""bootstrap_admin — alta idempotente del admin del CRM en prod."""

import pytest
from sqlalchemy import text

from chatbot_api.core.db import get_engine, get_session_factory
from chatbot_api.core.settings import get_settings


def _reset_caches() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


@pytest.mark.asyncio
async def test_bootstrap_admin_idempotent(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("ADMIN_EMAIL", "Boss@UPC.edu.pe")  # mixed case → se normaliza
    monkeypatch.setenv("ADMIN_NAME", "Boss")
    _reset_caches()

    from chatbot_api.scripts.bootstrap_admin import bootstrap_admin

    try:
        await bootstrap_admin()
        await bootstrap_admin()  # 2da vez: no debe romper (ON CONFLICT)

        async with get_session_factory()() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT name, active FROM admins "
                        "WHERE email = 'boss@upc.edu.pe'"
                    )
                )
            ).first()
            assert row is not None, "el admin debió crearse"
            assert row.name == "Boss"
            assert row.active is True
            # limpieza: no dejar la fila para otros tests
            await s.execute(text("DELETE FROM admins WHERE email = 'boss@upc.edu.pe'"))
            await s.commit()
        await get_engine().dispose()
    finally:
        _reset_caches()


@pytest.mark.asyncio
async def test_bootstrap_admin_noop_without_email(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    monkeypatch.setenv("ADMIN_EMAIL", "")
    _reset_caches()

    from chatbot_api.scripts.bootstrap_admin import bootstrap_admin

    try:
        await bootstrap_admin()  # sin email → no-op, no debe lanzar
    finally:
        await get_engine().dispose()
        _reset_caches()
