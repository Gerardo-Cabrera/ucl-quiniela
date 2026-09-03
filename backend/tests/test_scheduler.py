"""
Tests de los jobs del scheduler: cálculo de puntos y sync de primer gol.

Regresión del bug de carrera: calculate_pending_points (cada 30 min) puntuaba
partidos finalizados antes de que sync_first_goals (cada hora) trajera el dato
del primer gol, perdiendo esos puntos permanentemente.
"""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.models.player import Player
from app.models.top8_pick import Top8Pick
from app.crud.app_state import app_state_crud
from sqlalchemy import select
from app.services import scheduler as scheduler_module
from app.services import ucl_api
from tests.conftest import TestSessionLocal, SEED_TEAMS


@pytest.fixture(autouse=True)
def _use_test_db(monkeypatch):
    """Los jobs usan AsyncSessionLocal directamente: apuntarlos a la BD de test."""
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", TestSessionLocal)


async def _seed(
    *,
    home_score: int = 2,
    away_score: int = 1,
    first_goal_resolved: bool = False,
    actual_scorer_id: int | None = 10,
    match_date: datetime | None = None,
    predicted_home: int = 2,
    predicted_away: int = 1,
    predicted_scorer_id: int | None = 10,
) -> int:
    """Crea usuario + partido finalizado + predicción. Retorna el id de la predicción.

    `first_goal_resolved`: si el job de eventos ya resolvió el primer gol
    (sentinel `first_goal_team`) y, en ese caso, qué jugador lo anotó.
    """
    async with TestSessionLocal() as session:
        user = User(team_name="Jax FC", email="sched@test.com", hashed_password="x")
        session.add(user)
        await session.flush()

        match = Match(
            api_fixture_id=5001,
            home_team="Real Madrid",
            away_team="Barcelona",
            home_score=home_score,
            away_score=away_score,
            first_goal_team="Real Madrid" if first_goal_resolved else None,
            first_goal_player_id=actual_scorer_id if first_goal_resolved else None,
            phase=MatchPhase.LEAGUE,
            status=MatchStatus.FINISHED,
            match_date=match_date or datetime.now(timezone.utc) - timedelta(hours=3),
        )
        session.add(match)
        await session.flush()

        prediction = Prediction(
            user_id=user.id,
            match_id=match.id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            first_goal_player_id=predicted_scorer_id,
        )
        session.add(prediction)
        await session.commit()
        return prediction.id


async def _get_prediction(prediction_id: int) -> Prediction:
    async with TestSessionLocal() as session:
        return await session.get(Prediction, prediction_id)


@pytest.mark.asyncio
async def test_calc_waits_for_first_goal():
    """Partido reciente con goles pero sin primer gol sincronizado: no puntuar aún."""
    pred_id = await _seed(first_goal_resolved=False)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is False
    assert pred.points_earned == 0


@pytest.mark.asyncio
async def test_calc_scores_with_first_goal_known():
    """Con el primer gol disponible: resultado exacto (8) + primer gol (3) = 11."""
    pred_id = await _seed(first_goal_resolved=True, actual_scorer_id=10)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 11


@pytest.mark.asyncio
async def test_calc_zero_zero_does_not_wait():
    """Un 0-0 no tiene primer gol que esperar: se puntúa de inmediato."""
    pred_id = await _seed(home_score=0, away_score=0, predicted_home=0, predicted_away=0)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 8  # resultado exacto en fase de liga


@pytest.mark.asyncio
async def test_calc_grace_period_unblocks():
    """Si la API nunca entrega el primer gol, tras el plazo de gracia se
    puntúa sin él para no dejar puntos bloqueados."""
    old_date = datetime.now(timezone.utc) - timedelta(
        hours=scheduler_module.settings.FIRST_GOAL_GRACE_HOURS + 12
    )
    pred_id = await _seed(first_goal_resolved=False, match_date=old_date)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 8  # exacto, sin punto de primer gol


@pytest.mark.asyncio
async def test_sync_first_goals_self_heals(monkeypatch):
    """Si una predicción se puntuó sin el primer gol, al llegar el dato se
    resetea y el siguiente cálculo otorga los puntos completos."""
    pred_id = await _seed(first_goal_resolved=False)

    # Simular el estado del bug: ya calculada sin el punto de primer gol.
    async with TestSessionLocal() as session:
        pred = await session.get(Prediction, pred_id)
        pred.is_calculated = True
        pred.points_earned = 8
        await session.commit()

    async def fake_fetch_events(fixture_id: int) -> list[dict]:
        return [
            {"time": {"elapsed": 55, "extra": None}, "type": "Card",
             "detail": "Yellow Card", "team": {"name": "Barcelona"},
             "player": {"id": 20, "name": "Lewandowski"}},
            {"time": {"elapsed": 23, "extra": None}, "type": "Goal",
             "detail": "Normal Goal", "team": {"name": "Real Madrid"},
             "player": {"id": 10, "name": "Vinicius Jr"}},
        ]

    monkeypatch.setattr(ucl_api, "fetch_fixture_events", fake_fetch_events)

    await scheduler_module._do_sync_first_goals()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is False  # marcada para recálculo

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 11  # ahora con el punto de primer gol


@pytest.mark.asyncio
async def test_retry_stops_on_auth_error():
    """Un 403/401 de la API es de configuración (no transitorio): no se reintenta."""
    import httpx

    calls = 0

    async def failing():
        nonlocal calls
        calls += 1
        req = httpx.Request("GET", "https://api-football-v1.p.rapidapi.com/v3/leagues?id=2")
        raise httpx.HTTPStatusError(
            "Client error '403 Forbidden'", request=req, response=httpx.Response(403, request=req)
        )

    ok, result = await scheduler_module._retry(failing, "sync_fixtures")
    assert ok is False
    assert result is None
    assert calls == 1  # sin reintentos (con retry habrían sido JOB_MAX_RETRIES)


# ── SYNC DE PLANTILLAS ───────────────────────────────────────────────────────


async def _add_match(
    api_fixture_id: int, home_id: int, away_id: int, *,
    status: MatchStatus, phase: MatchPhase = MatchPhase.LEAGUE,
) -> None:
    async with TestSessionLocal() as session:
        session.add(Match(
            api_fixture_id=api_fixture_id,
            home_team=f"T{home_id}", away_team=f"T{away_id}",
            home_team_api_id=home_id, away_team_api_id=away_id,
            phase=phase, status=status,
            match_date=datetime.now(timezone.utc) + timedelta(days=1),
        ))
        await session.commit()


@pytest.mark.asyncio
async def test_team_ids_pending_only_keeps_alive_teams():
    """Clubes (Top 8): todos los equipos con partidos. Plantillas: solo los que
    tienen partidos SIN finalizar (vivos); un eliminado no gasta cuota."""
    await _add_match(1, 541, 529, status=MatchStatus.FINISHED)      # liga ya jugada
    await _add_match(2, 541, 50, status=MatchStatus.SCHEDULED, phase=MatchPhase.KNOCKOUT_PLAYOFFS)
    await _add_match(3, 33, 85, status=MatchStatus.SCHEDULED)       # liga pendiente

    assert await scheduler_module._team_ids_in_matches() == {541, 529, 50, 33, 85}
    # 529 solo tiene partidos finalizados → eliminado: fuera del sync de plantillas.
    assert await scheduler_module._team_ids_in_matches(pending_only=True) == {541, 50, 33, 85}


@pytest.mark.asyncio
async def test_sync_players_prunes_departed_and_keeps_failed_teams(monkeypatch):
    """Tras el sync se añaden las altas y se ELIMINAN las bajas del equipo
    sincronizado; un equipo cuya petición falla o vuelve vacía (p. ej. rateLimit)
    conserva su plantilla intacta (no se poda a ciegas)."""
    monkeypatch.setattr(scheduler_module.settings, "API_REQUESTS_PER_MINUTE", 60_000)  # sin esperas
    # conftest siembra Real Madrid (541): 10 Vinicius, 11 Bellingham; Barcelona (529): 20, 21.
    await _add_match(1, 541, 529, status=MatchStatus.SCHEDULED)
    await _add_match(2, 50, 33, status=MatchStatus.SCHEDULED)

    async def fake_fetch_squad(team_api_id: int) -> list[dict]:
        if team_api_id == 541:   # Bellingham (11) se fue; llega Mbappé (12)
            return [{"team": {"id": 541, "name": "Real Madrid"},
                     "players": [{"id": 10, "name": "Vinicius Jr", "position": "Attacker"},
                                 {"id": 12, "name": "Mbappé", "position": "Attacker"}]}]
        if team_api_id == 529:   # fallo de red
            raise RuntimeError("boom")
        return []                # 50 y 33: respuesta vacía

    monkeypatch.setattr(ucl_api, "fetch_squad", fake_fetch_squad)
    await scheduler_module._do_sync_players()

    async with TestSessionLocal() as session:
        rows = (await session.execute(select(Player.team_api_id, Player.api_player_id))).all()
    by_team: dict[int, set[int]] = {}
    for tid, pid in rows:
        by_team.setdefault(tid, set()).add(pid)
    assert by_team[541] == {10, 12}   # baja eliminada, alta añadida
    assert by_team[529] == {20, 21}   # intacto: la petición falló


@pytest.mark.asyncio
async def test_fetch_paced_spaces_requests(monkeypatch):
    """Peticiones en secuencia con 60/API_REQUESTS_PER_MINUTE s entre ellas; un fallo
    individual no aborta el lote (se devuelve por posición)."""
    monkeypatch.setattr(scheduler_module.settings, "API_REQUESTS_PER_MINUTE", 30)
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(scheduler_module.asyncio, "sleep", fake_sleep)

    async def fetch(key: int) -> int:
        if key == 2:
            raise ValueError("x")
        return key * 10

    results = await scheduler_module._fetch_paced(fetch, [1, 2, 3])
    assert results[0] == 10 and isinstance(results[1], ValueError) and results[2] == 30
    assert sleeps == [2.0, 2.0]   # n-1 esperas de 60/30 s


# ── TOP 8 AUTOMÁTICO AL TERMINAR LA FASE DE LIGA ─────────────────────────────

# 7 en posición exacta (1.º-7.º) y Juventus (9.º real) fuera → 35 pts.
PICKS = ["Real Madrid", "Manchester City", "Bayern Munich", "Barcelona",
         "Arsenal", "Liverpool", "Inter Milan", "Juventus"]
REAL_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9]   # ids de conftest; PSG (8) es 8.º


async def _seed_top8(picks: list[str] = PICKS, *, calculated: bool = False) -> None:
    async with TestSessionLocal() as session:
        user = User(team_name="Top FC", email="top8@test.com", hashed_password="x")
        session.add(user)
        await session.flush()
        session.add_all(
            Top8Pick(user_id=user.id, position=i, team_name=t, is_calculated=calculated)
            for i, t in enumerate(picks, start=1)
        )
        await session.commit()


def _standings(order: list[int], *, played: int) -> list[dict]:
    names = {t["api_team_id"]: t["name"] for t in SEED_TEAMS}
    return [{"rank": i, "team": {"id": tid, "name": names[tid]}, "all": {"played": played}}
            for i, tid in enumerate(order, start=1)]


def _fake_standings(monkeypatch, rows: list[dict]) -> list[bool]:
    """Parchea /standings y devuelve la lista donde se registra cada llamada."""
    calls: list[bool] = []

    async def fake() -> list[dict]:
        calls.append(True)
        return rows

    monkeypatch.setattr(ucl_api, "fetch_standings", fake)
    return calls


async def _top8_state() -> tuple[bool, int]:
    """(¿todos los picks puntuados?, suma de puntos)."""
    async with TestSessionLocal() as session:
        rows = (await session.execute(select(Top8Pick.is_calculated, Top8Pick.points_earned))).all()
    return all(c for c, _ in rows), sum(p for _, p in rows)


@pytest.mark.asyncio
async def test_top8_auto_calculated_when_league_ends(monkeypatch):
    """Con TODA la liga finalizada, el job toma el Top 8 real de /standings (por id →
    nombres de `teams`) y puntúa a todos."""
    await _add_match(1, 1, 2, status=MatchStatus.FINISHED)   # 2 partidos, 2 equipos locales
    await _add_match(2, 3, 4, status=MatchStatus.FINISHED)   # → 2 partidos por equipo
    await _seed_top8()
    calls = _fake_standings(monkeypatch, _standings(REAL_ORDER, played=2))

    await scheduler_module._do_calculate_top8()

    assert calls == [True]
    assert await _top8_state() == (True, 35)
    # Queda constancia del Top 8 real (los 8 primeros de la clasificación, por nombre).
    async with TestSessionLocal() as session:
        assert await app_state_crud.get_top8_actual(session) == [t["name"] for t in SEED_TEAMS][:8]


@pytest.mark.asyncio
async def test_top8_waits_for_league_end(monkeypatch):
    """Mientras quede liga por jugar no consulta la API ni puntúa."""
    await _add_match(1, 1, 2, status=MatchStatus.FINISHED)
    await _add_match(2, 3, 4, status=MatchStatus.SCHEDULED)
    await _seed_top8()
    calls = _fake_standings(monkeypatch, _standings(REAL_ORDER, played=2))

    await scheduler_module._do_calculate_top8()

    assert calls == []
    assert await _top8_state() == (False, 0)


@pytest.mark.asyncio
async def test_top8_waits_for_complete_standings(monkeypatch):
    """Liga terminada en BD pero la API aún no refleja todos los partidos jugados:
    no puntúa (se reintenta en la próxima corrida)."""
    await _add_match(1, 1, 2, status=MatchStatus.FINISHED)
    await _add_match(2, 3, 4, status=MatchStatus.FINISHED)
    await _seed_top8()
    calls = _fake_standings(monkeypatch, _standings(REAL_ORDER, played=1))

    await scheduler_module._do_calculate_top8()

    assert calls == [True]
    assert await _top8_state() == (False, 0)


@pytest.mark.asyncio
async def test_top8_auto_skips_when_already_calculated(monkeypatch):
    """Sin picks pendientes no vuelve a llamar a la API (corre una sola vez)."""
    await _add_match(1, 1, 2, status=MatchStatus.FINISHED)
    await _seed_top8(calculated=True)
    calls = _fake_standings(monkeypatch, _standings(REAL_ORDER, played=2))

    await scheduler_module._do_calculate_top8()

    assert calls == []


@pytest.mark.asyncio
async def test_sync_players_single_flight(monkeypatch):
    """Con una corrida en curso, otra llamada (manual o programada) se omite en vez de
    solaparse: duplicaría el ritmo de peticiones y reconciliaría dos instantáneas."""
    started, release = asyncio.Event(), asyncio.Event()
    runs: list[bool] = []

    async def slow_sync() -> None:
        runs.append(True)
        started.set()
        await release.wait()

    monkeypatch.setattr(scheduler_module, "_do_sync_players", slow_sync)
    first = asyncio.create_task(scheduler_module.sync_players())
    await started.wait()
    assert scheduler_module.players_sync_in_progress()

    await scheduler_module.sync_players()   # se omite: ni espera ni duplica
    assert runs == [True]

    release.set()
    await first
    assert not scheduler_module.players_sync_in_progress()


# ── ESTADÍSTICAS DEL TORNEO (goleadores / asistidores) ───────────────────────


def _api_top_player(pid: int, name: str, team: str, goals: int, assists: int) -> dict:
    """Entrada cruda de /players/topscorers|topassists (forma de API-Football)."""
    return {"player": {"id": pid, "name": name, "photo": f"https://img/{pid}.png"},
            "statistics": [{"team": {"name": team}, "games": {"appearences": 8},
                            "goals": {"total": goals, "assists": assists}}]}


@pytest.mark.asyncio
async def test_sync_tournament_stats_skips_without_finished_matches(monkeypatch):
    """Pretemporada (sin partidos finalizados): no consulta la API."""
    calls: list[str] = []

    async def fake(kind: str) -> list[dict]:
        calls.append(kind)
        return []

    monkeypatch.setattr(ucl_api, "fetch_top_players", fake)
    await _add_match(1, 541, 529, status=MatchStatus.SCHEDULED)
    await scheduler_module._do_sync_tournament_stats()
    assert calls == []


@pytest.mark.asyncio
async def test_sync_tournament_stats_stores_top_players(monkeypatch):
    """Con partidos finalizados trae ambos rankings, los parsea (jugador, equipo,
    goles, asistencias, partidos) y guarda hasta 10 de cada uno."""
    await _add_match(1, 541, 529, status=MatchStatus.FINISHED)

    async def fake(kind: str) -> list[dict]:
        if kind == "topscorers":
            return [_api_top_player(i, f"Goleador {i}", "Real Madrid", 12 - i, 1) for i in range(1, 13)]
        return [_api_top_player(20, "Asistidor", "Barcelona", 2, 6)]

    monkeypatch.setattr(ucl_api, "fetch_top_players", fake)
    await scheduler_module._do_sync_tournament_stats()

    async with TestSessionLocal() as session:
        stats = await app_state_crud.get_tournament_stats(session)
    assert len(stats["top_scorers"]) == 10   # recorta a 10
    assert stats["top_scorers"][0] == {
        "player_id": 1, "name": "Goleador 1", "photo": "https://img/1.png",
        "team": "Real Madrid", "goals": 11, "assists": 1, "matches": 8,
    }
    assert stats["top_assists"] == [{
        "player_id": 20, "name": "Asistidor", "photo": "https://img/20.png",
        "team": "Barcelona", "goals": 2, "assists": 6, "matches": 8,
    }]
