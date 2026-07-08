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
