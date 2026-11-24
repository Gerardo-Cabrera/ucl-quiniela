"""Sesión de BD por request: los GET van en autocommit (solo lectura, sin BEGIN/COMMIT)
y el resto de métodos en transacción. La suite sustituye `get_db` por una sesión SQLite
(conftest), así que aquí se prueba la dependencia real: qué fábrica elige y cómo están
montadas las dos sobre el mismo pool."""
import pytest
from starlette.requests import Request

import app.database as database
from tests.conftest import TestSessionLocal


def _request(method: str) -> Request:
    return Request({"type": "http", "method": method, "path": "/", "headers": []})


@pytest.mark.asyncio
@pytest.mark.parametrize("method, expected", [
    ("GET", "read_only"),
    ("POST", "transactional"),
    ("PUT", "transactional"),
    ("PATCH", "transactional"),
    ("DELETE", "transactional"),
])
async def test_get_db_picks_the_session_by_method(monkeypatch, method, expected):
    used: list[str] = []

    def factory(name: str):
        def make():
            used.append(name)
            return TestSessionLocal()
        return make

    monkeypatch.setattr(database, "ReadOnlySessionLocal", factory("read_only"))
    monkeypatch.setattr(database, "AsyncSessionLocal", factory("transactional"))

    sessions = [session async for session in database.get_db(_request(method))]

    assert used == [expected]
    assert len(sessions) == 1


def test_session_factories_share_one_pool_with_their_own_isolation():
    read_only = database.ReadOnlySessionLocal.kw["bind"]
    transactional = database.AsyncSessionLocal.kw["bind"]

    # Lecturas: el engine base (autocommit). Escrituras y jobs: transacción explícita.
    assert read_only is database.engine
    assert "isolation_level" not in read_only.sync_engine.get_execution_options()
    assert transactional.sync_engine.get_execution_options()["isolation_level"] == "READ COMMITTED"
    # Un solo pool: no se duplican las conexiones contra el pooler de la BD.
    assert transactional.sync_engine.pool is read_only.sync_engine.pool
