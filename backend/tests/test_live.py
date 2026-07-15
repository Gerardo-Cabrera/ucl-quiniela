"""
Tests de los datos de partido EN VIVO: parseo de minuto (elapsed) y penales,
fallback de finalización, y el sync adaptativo (detección de en-juego y de
partidos recién finalizados).
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.match import Match, MatchPhase, MatchStatus
from app.models.team import Team
from app.services import ucl_api
from app.services import scheduler as scheduler_module
from tests.conftest import TestSessionLocal


def _fixture(*, fid=8001, status="1H", elapsed=55, home_goals=1, away_goals=0,
             round_="League Stage", pen_home=None, pen_away=None, minutes_ago=5):
    date = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    return {
        "fixture": {"id": fid, "date": date, "status": {"short": status, "elapsed": elapsed}},
        "teams": {"home": {"id": 541, "name": "Real Madrid", "logo": "h.png"},
                  "away": {"id": 529, "name": "Barcelona", "logo": "a.png"}},
        "goals": {"home": home_goals, "away": away_goals},
        "league": {"round": round_},
        "score": {"penalty": {"home": pen_home, "away": pen_away}},
    }


# ── PARSEO ──────────────────────────────────────────────────────────────────────

def test_parse_elapsed_live():
    parsed = ucl_api.parse_fixture(_fixture(status="1H", elapsed=67))
    assert parsed["status"] == MatchStatus.LIVE
    assert parsed["elapsed"] == 67
    assert parsed["penalty_home"] is None


def test_parse_penalties():
    parsed = ucl_api.parse_fixture(
        _fixture(status="PEN", round_="Round of 16", home_goals=1, away_goals=1,
                 pen_home=4, pen_away=3)
    )
    assert parsed["status"] == MatchStatus.FINISHED
    assert parsed["penalty_home"] == 4
    assert parsed["penalty_away"] == 3


def test_parse_fallback_finishes_stuck_league_match():
    """Partido de liga aún LIVE mucho después del kickoff → se da por finalizado."""
    parsed = ucl_api.parse_fixture(
        _fixture(status="1H", round_="League Stage", minutes_ago=200)
    )
    assert parsed["status"] == MatchStatus.FINISHED


def test_parse_no_fallback_for_knockout():
    """Una eliminatoria puede ir a prórroga/penales: se respeta el estado de la API."""
    parsed = ucl_api.parse_fixture(
        _fixture(status="1H", round_="Final", minutes_ago=200)
    )
    assert parsed["status"] == MatchStatus.LIVE


def test_parse_recent_live_stays_live():
    parsed = ucl_api.parse_fixture(
        _fixture(status="1H", round_="League Stage", minutes_ago=10)
    )
    assert parsed["status"] == MatchStatus.LIVE


def test_parse_skips_fase_previa():
    """Las rondas de clasificación (fase previa) se descartan: parse_fixture → None.
    'Play-offs' (clasificación) es distinto de 'Knockout Round Play-offs' (oficial)."""
    assert ucl_api.parse_fixture(_fixture(round_="3rd Qualifying Round")) is None
    assert ucl_api.parse_fixture(_fixture(round_="Play-offs")) is None


def test_parse_league_stage_matchday():
    """La fase de liga del formato nuevo llega como 'League Stage - N' (jornada)."""
    parsed = ucl_api.parse_fixture(_fixture(round_="League Stage - 3"))
    assert parsed is not None
    assert parsed["phase"] == MatchPhase.LEAGUE


# ── TEMPORADA Y CLUBES (vía API) ────────────────────────────────────────────────

def test_parse_team():
    parsed = ucl_api.parse_team(
        {"team": {"id": 541, "name": "Real Madrid", "code": "MAD", "country": "Spain", "logo": "x.png"}}
    )
    assert parsed == {
        "api_team_id": 541, "name": "Real Madrid",
        "code": "MAD", "country": "Spain", "logo": "x.png",
    }


@pytest.mark.asyncio
async def test_resolve_season_uses_config():
    """Con UCL_SEASON configurado (>0) no llama a la API: devuelve la temporada fija."""
    assert await ucl_api.resolve_season() == 2026


# ── SYNC ADAPTATIVO ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _use_test_db(monkeypatch):
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", TestSessionLocal)


async def _add_match(**overrides) -> int:
    defaults = dict(
        api_fixture_id=8001, home_team="Real Madrid", away_team="Barcelona",
        phase=MatchPhase.LEAGUE, status=MatchStatus.LIVE,
        match_date=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    defaults.update(overrides)
    async with TestSessionLocal() as session:
        m = Match(**defaults)
        session.add(m)
        await session.commit()
        await session.refresh(m)
        return m.id


@pytest.mark.asyncio
async def test_has_match_in_play_true():
    await _add_match(status=MatchStatus.LIVE)
    assert await scheduler_module._has_match_in_play(datetime.now(timezone.utc)) is True


@pytest.mark.asyncio
async def test_has_match_in_play_false_when_finished():
    await _add_match(status=MatchStatus.FINISHED)
    assert await scheduler_module._has_match_in_play(datetime.now(timezone.utc)) is False


@pytest.mark.asyncio
async def test_sync_fixtures_reports_newly_finished(monkeypatch):
    """Un partido que pasa a FINISHED en este sync se reporta (para puntuar ya)."""
    match_id = await _add_match(status=MatchStatus.LIVE)

    async def fake_fetch_fixtures():
        return [_fixture(fid=8001, status="FT", home_goals=2, away_goals=1)]

    monkeypatch.setattr(ucl_api, "fetch_fixtures", fake_fetch_fixtures)

    newly_finished = await scheduler_module._do_sync_fixtures()
    assert newly_finished == [match_id]

    async with TestSessionLocal() as session:
        m = await session.get(Match, match_id)
        assert m.status == MatchStatus.FINISHED
        assert m.home_score == 2 and m.away_score == 1


@pytest.mark.asyncio
async def test_sync_fixtures_skips_fase_previa(monkeypatch):
    """El sync descarta los fixtures de fase previa y solo persiste los oficiales."""
    async def fake_fetch_fixtures():
        return [
            _fixture(fid=9001, round_="2nd Qualifying Round"),
            _fixture(fid=9002, round_="League Stage - 1"),
        ]

    monkeypatch.setattr(ucl_api, "fetch_fixtures", fake_fetch_fixtures)
    await scheduler_module._do_sync_fixtures()

    async with TestSessionLocal() as session:
        ids = {r[0] for r in (await session.execute(select(Match.api_fixture_id))).all()}
    assert ids == {9002}


@pytest.mark.asyncio
async def test_sync_teams_skipped_without_matches(monkeypatch):
    """Sin partidos oficiales en BD, el sync de clubes ni siquiera llama a la API."""
    called = False

    async def fake_fetch_teams():
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(ucl_api, "fetch_teams", fake_fetch_teams)
    await scheduler_module._do_sync_teams()
    assert called is False


@pytest.mark.asyncio
async def test_sync_teams_runs_with_matches(monkeypatch):
    """Con al menos un partido oficial en BD, el sync de clubes sí persiste."""
    await _add_match()

    async def fake_fetch_teams():
        return [{"team": {"id": 999, "name": "Test United", "code": "TU",
                          "country": "England", "logo": "x.png"}}]

    monkeypatch.setattr(ucl_api, "fetch_teams", fake_fetch_teams)
    await scheduler_module._do_sync_teams()

    async with TestSessionLocal() as session:
        names = {r[0] for r in (await session.execute(select(Team.name))).all()}
    assert "Test United" in names
