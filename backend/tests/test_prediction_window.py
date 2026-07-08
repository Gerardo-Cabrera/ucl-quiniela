"""Ventana de envío de pronósticos: plazo por jornada + interruptor de prórroga.

- Unit: la regla pura (`_limit`/`_predictable`) con fechas explícitas.
- CRUD: `day_first_kickoffs` (primer partido de cada día en la zona del torneo).
- Integración: el flag `predictable` de /matches, el interruptor admin /predictions/override
  y los rechazos del POST. Se usan partidos en días distintos para no depender de la
  medianoche local (grouping determinista).
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient

from app.config import settings
from app.models.match import Match, MatchPhase, MatchStatus
from app.services.prediction_window import _limit, _predictable
from app.crud import match_crud
from tests.conftest import TestSessionLocal

_MADRID = ZoneInfo("Europe/Madrid")
_LEAD = settings.PREDICTION_LEAD_MINUTES


async def _create_match(**overrides) -> int:
    defaults = dict(
        api_fixture_id=9100, home_team="Real Madrid", away_team="Barcelona",
        phase=MatchPhase.LEAGUE, status=MatchStatus.SCHEDULED,
        match_date=datetime.now(timezone.utc) + timedelta(days=2),
    )
    defaults.update(overrides)
    async with TestSessionLocal() as session:
        match = Match(**defaults)
        session.add(match)
        await session.commit()
        await session.refresh(match)
        return match.id


# ── Unit: la regla ──────────────────────────────────────────────────────────

def test_limit_off_resta_el_lead():
    fk = datetime(2027, 2, 16, 20, 0, tzinfo=timezone.utc)
    assert _limit(fk, override=False) == fk - timedelta(minutes=_LEAD)
    assert _limit(fk, override=True) == fk  # con prórroga, hasta el kickoff


def test_predictable_rules():
    now = datetime(2027, 2, 16, 12, 0, tzinfo=timezone.utc)
    scheduled = Match(status=MatchStatus.SCHEDULED)

    # Holgado: antes del plazo → pronosticable.
    assert _predictable(scheduled, now + timedelta(hours=3), False, now) is True
    # Dentro del lead (a 30 min del kickoff, lead 60) → cerrado sin prórroga...
    assert _predictable(scheduled, now + timedelta(minutes=30), False, now) is False
    # ...pero abierto con la prórroga (hasta el propio kickoff).
    assert _predictable(scheduled, now + timedelta(minutes=30), True, now) is True
    # Ya empezó el primer partido del día → cerrado incluso con prórroga.
    assert _predictable(scheduled, now - timedelta(minutes=1), True, now) is False
    # Sin fecha de jornada o partido no programado → cerrado.
    assert _predictable(scheduled, None, True, now) is False
    assert _predictable(Match(status=MatchStatus.LIVE), now + timedelta(hours=3), True, now) is False


# ── CRUD: primer partido de cada jornada ─────────────────────────────────────

@pytest.mark.asyncio
async def test_day_first_kickoffs_earliest_per_day():
    # Feb 16 (Madrid): 18:00Z y 21:00Z → el primero es 18:00Z. Feb 17: 20:00Z.
    await _create_match(api_fixture_id=1, match_date=datetime(2027, 2, 16, 21, 0, tzinfo=timezone.utc))
    await _create_match(api_fixture_id=2, match_date=datetime(2027, 2, 16, 18, 0, tzinfo=timezone.utc))
    await _create_match(api_fixture_id=3, match_date=datetime(2027, 2, 17, 20, 0, tzinfo=timezone.utc))

    async with TestSessionLocal() as session:
        firsts = await match_crud.day_first_kickoffs(session, _MADRID)

    assert firsts[date(2027, 2, 16)] == datetime(2027, 2, 16, 18, 0, tzinfo=timezone.utc)
    assert firsts[date(2027, 2, 17)] == datetime(2027, 2, 17, 20, 0, tzinfo=timezone.utc)


# ── Integración: flag predictable en /matches ────────────────────────────────

@pytest.mark.asyncio
async def test_matches_expose_predictable(auth_client: AsyncClient):
    future = await _create_match(api_fixture_id=1, match_date=datetime.now(timezone.utc) + timedelta(days=2))
    within = await _create_match(api_fixture_id=2, match_date=datetime.now(timezone.utc) + timedelta(minutes=30))

    matches = {m["id"]: m for m in (await auth_client.get("/api/matches/")).json()}
    assert matches[future]["predictable"] is True      # holgado
    assert matches[within]["predictable"] is False     # dentro del plazo (lead)


@pytest.mark.asyncio
async def test_prediction_within_lead_rejected(auth_client: AsyncClient):
    within = await _create_match(match_date=datetime.now(timezone.utc) + timedelta(minutes=30))
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": within, "predicted_home": 1, "predicted_away": 0,
    })
    assert resp.status_code == 400
    assert "cerró" in resp.json()["detail"]


# ── Integración: interruptor de prórroga (admin) ─────────────────────────────

@pytest.mark.asyncio
async def test_override_default_off(admin_client: AsyncClient):
    data = (await admin_client.get("/api/predictions/override")).json()
    assert data == {"enabled": False, "lead_minutes": _LEAD}


@pytest.mark.asyncio
async def test_override_requires_admin(auth_client: AsyncClient):
    assert (await auth_client.get("/api/predictions/override")).status_code == 403
    assert (await auth_client.put("/api/predictions/override", json={"enabled": True})).status_code == 403


@pytest.mark.asyncio
async def test_override_reopens_within_lead(admin_client: AsyncClient):
    within = await _create_match(match_date=datetime.now(timezone.utc) + timedelta(minutes=30))

    # Sin prórroga: cerrado.
    matches = {m["id"]: m for m in (await admin_client.get("/api/matches/")).json()}
    assert matches[within]["predictable"] is False

    # Se activa la prórroga.
    put = (await admin_client.put("/api/predictions/override", json={"enabled": True})).json()
    assert put["enabled"] is True

    # Ahora pronosticable y el POST se acepta.
    matches = {m["id"]: m for m in (await admin_client.get("/api/matches/")).json()}
    assert matches[within]["predictable"] is True
    resp = await admin_client.post("/api/predictions/", json={
        "match_id": within, "predicted_home": 2, "predicted_away": 1,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_override_does_not_reopen_started_match(admin_client: AsyncClient):
    """La prórroga nunca permite pronosticar un partido cuyo día ya arrancó."""
    started = await _create_match(match_date=datetime.now(timezone.utc) - timedelta(minutes=10))
    await admin_client.put("/api/predictions/override", json={"enabled": True})

    matches = {m["id"]: m for m in (await admin_client.get("/api/matches/")).json()}
    assert matches[started]["predictable"] is False
    resp = await admin_client.post("/api/predictions/", json={
        "match_id": started, "predicted_home": 1, "predicted_away": 0,
    })
    assert resp.status_code == 400
    assert "comenzó" in resp.json()["detail"]
