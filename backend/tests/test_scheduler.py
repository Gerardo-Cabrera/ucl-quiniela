"""
Tests de los jobs del scheduler: cálculo de puntos y sync de primer gol.

Regresión del bug de carrera: calculate_pending_points (cada 30 min) puntuaba
partidos finalizados antes de que sync_first_goals (cada hora) trajera el dato
del primer gol, perdiendo esos puntos permanentemente.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.models.player import Player
from sqlalchemy import select
from app.services import scheduler as scheduler_module
from app.services import ucl_api
from tests.conftest import TestSessionLocal


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
