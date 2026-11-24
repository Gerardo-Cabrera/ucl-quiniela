"""Arranque de la app: migraciones siempre; los jobs, solo si SCHEDULER_ENABLED. La suite
no dispara el lifespan (ASGITransport), así que aquí se recorre a mano con las piezas
externas sustituidas (ni alembic ni APScheduler reales)."""
import pytest

import app.main as main


@pytest.fixture
def lifecycle(monkeypatch):
    events: list[str] = []

    async def fake_start() -> None:
        events.append("start")

    async def fake_close() -> None:
        events.append("close_client")

    monkeypatch.setattr(main, "run_migrations", lambda: events.append("migrations"))
    monkeypatch.setattr(main, "start_scheduler", fake_start)
    monkeypatch.setattr(main, "stop_scheduler", lambda: events.append("stop"))
    monkeypatch.setattr(main, "close_client", fake_close)
    return events


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_the_scheduler_by_default(lifecycle, monkeypatch):
    monkeypatch.setattr(main.settings, "SCHEDULER_ENABLED", True)
    async with main.lifespan(main.app):
        assert lifecycle == ["migrations", "start"]
    assert lifecycle == ["migrations", "start", "stop", "close_client"]


@pytest.mark.asyncio
async def test_lifespan_without_scheduler_only_migrates(lifecycle, monkeypatch):
    """Con SCHEDULER_ENABLED=false la instancia sirve la API pero no arranca (ni para) jobs:
    es la que se levanta de reserva mientras otra sigue sincronizando."""
    monkeypatch.setattr(main.settings, "SCHEDULER_ENABLED", False)
    async with main.lifespan(main.app):
        assert lifecycle == ["migrations"]
    assert lifecycle == ["migrations", "close_client"]


def test_scheduler_is_enabled_unless_configured_otherwise(monkeypatch):
    from app.config import Settings

    # Sin .env ni variable de entorno (en local alguien puede tenerlo apagado a propósito).
    monkeypatch.delenv("SCHEDULER_ENABLED", raising=False)
    assert Settings(_env_file=None).SCHEDULER_ENABLED is True
    assert Settings(_env_file=None, SCHEDULER_ENABLED="false").SCHEDULER_ENABLED is False
