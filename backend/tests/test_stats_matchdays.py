"""
Tests de las vistas Aciertos (/stats) y MVPs (/matchdays).

Siembran un partido finalizado y puntuado con dos participantes: uno acierta
marcador exacto + primer goleador, el otro falla. Comprueban los rankings.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from sqlalchemy import select
from tests.conftest import TestSessionLocal


async def _seed_scored_match():
    """Real Madrid 2-1 Barcelona, primer gol jugador 10. Dos participantes:
    Jax FC (user 1, acierta todo) y Megalink FC (falla)."""
    async with TestSessionLocal() as session:
        # user 1 (Jax FC) ya existe vía auth_client; añadimos el segundo.
        rival = User(team_name="Megalink FC", email="rival@test.com", hashed_password="x")
        session.add(rival)
        match = Match(
            api_fixture_id=7001,
            home_team="Real Madrid", away_team="Barcelona",
            home_score=2, away_score=1,
            first_goal_team="Real Madrid", first_goal_player_id=10, first_goal_player="Vinicius Jr",
            phase=MatchPhase.LEAGUE, round_number=1, status=MatchStatus.FINISHED,
            match_date=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        session.add(match)
        await session.flush()

        session.add_all([
            # Jax FC (user 1): marcador exacto + victoria + primer goleador → 16 pts
            Prediction(user_id=1, match_id=match.id, predicted_home=2, predicted_away=1,
                       first_goal_player_id=10, first_goal_player="Vinicius Jr",
                       points_earned=16, is_calculated=True),
            # Megalink FC: falla marcador y goleador → 0 pts
            Prediction(user_id=rival.id, match_id=match.id, predicted_home=0, predicted_away=0,
                       first_goal_player_id=20, first_goal_player="Lewandowski",
                       points_earned=0, is_calculated=True),
        ])
        await session.commit()


@pytest.mark.asyncio
async def test_stats_rankings(auth_client: AsyncClient):
    await _seed_scored_match()
    data = (await auth_client.get("/api/stats/")).json()

    assert data["first_goal_ranking"] == [{"team_name": "Jax FC", "count": 1}]
    assert data["exact_ranking"] == [{"team_name": "Jax FC", "count": 1}]
    assert data["top_scores"] == [{"score": "2-1", "count": 1}]

    # Solo partidos con acierto de primer gol.
    assert len(data["first_goal_matches"]) == 1
    fg = data["first_goal_matches"][0]
    assert fg["scorer"] == "Vinicius Jr"
    assert fg["hitters"] == ["Jax FC"]

    # Solo partidos con acierto de marcador exacto.
    assert len(data["exact_matches"]) == 1
    ex = data["exact_matches"][0]
    assert ex["score"] == "2-1"
    assert ex["hitters"] == ["Jax FC"]


@pytest.mark.asyncio
async def test_stats_only_hits_shown(auth_client: AsyncClient):
    """Un partido finalizado SIN aciertos no aparece en las listas por partido."""
    async with TestSessionLocal() as session:
        session.add(Match(
            api_fixture_id=7002, home_team="Real Madrid", away_team="Barcelona",
            home_score=3, away_score=0, first_goal_team="Real Madrid",
            first_goal_player_id=11, first_goal_player="Bellingham",
            phase=MatchPhase.LEAGUE, status=MatchStatus.FINISHED,
            match_date=datetime.now(timezone.utc) - timedelta(hours=5),
        ))
        await session.commit()
    # Nadie pronosticó ese partido → no debe listarse (ni en primer gol ni exacto).
    data = (await auth_client.get("/api/stats/")).json()
    assert data["first_goal_matches"] == []
    assert data["exact_matches"] == []


@pytest.mark.asyncio
async def test_stats_empty(auth_client: AsyncClient):
    """Sin partidos puntuados, todo vacío."""
    data = (await auth_client.get("/api/stats/")).json()
    assert data == {
        "first_goal_matches": [],
        "first_goal_ranking": [],
        "top_scores": [],
        "exact_matches": [],
        "exact_ranking": [],
    }


@pytest.mark.asyncio
async def test_matchdays_mvp(auth_client: AsyncClient):
    await _seed_scored_match()
    data = (await auth_client.get("/api/matchdays/")).json()

    assert len(data["days"]) == 1
    day = data["days"][0]
    assert day["mvp_points"] == 16
    assert day["mvps"] == ["Jax FC"]
    # Ambos participantes aparecen, ordenados por puntos desc.
    assert [e["team_name"] for e in day["entries"]] == ["Jax FC", "Megalink FC"]
    assert day["complete"] is True   # único partido del día: terminado y puntuado

    assert data["mvp_ranking"] == [{"team_name": "Jax FC", "count": 1}]
    # Jornada completa (ronda 1 de la fase de liga): con un solo día coincide con él.
    assert len(data["rounds"]) == 1
    rnd = data["rounds"][0]
    assert (rnd["phase"], rnd["round_number"], rnd["start"], rnd["end"]) == ("league", 1, day["date"], day["date"])
    assert rnd["mvps"] == ["Jax FC"] and rnd["mvp_points"] == 16 and rnd["complete"] is True


async def _add_round_match(*, ago: timedelta, round_number: int | None = None, phase=MatchPhase.LEAGUE,
                           status=MatchStatus.FINISHED, points: dict[int, int] | None = None,
                           calculated: bool = True) -> None:
    """Otro partido de la ronda (`round_number` en liga; en eliminatorias la `phase`)
    hace `ago`, con las predicciones (user_id -> puntos) indicadas. Para caer en el
    mismo día que el partido de `_seed_scored_match` (hace 3 h) sea cual sea la hora
    actual, usar el mismo instante: `ago=timedelta(hours=3)`."""
    async with TestSessionLocal() as session:
        match = Match(
            api_fixture_id=7100 + int(ago.total_seconds() // 3600), home_team="Bayern Munich", away_team="Manchester City",
            home_score=1, away_score=0, first_goal_team="Bayern Munich",
            phase=phase, round_number=round_number, status=status,
            match_date=datetime.now(timezone.utc) - ago,
        )
        session.add(match)
        await session.flush()
        session.add_all([
            Prediction(user_id=uid, match_id=match.id, predicted_home=1, predicted_away=0,
                       points_earned=pts, is_calculated=calculated)
            for uid, pts in (points or {}).items()
        ])
        await session.commit()


@pytest.mark.asyncio
async def test_matchdays_round_sums_its_days(auth_client: AsyncClient):
    """La jornada completa suma los puntos de todos sus días: el MVP del día puede
    no ser el de la jornada. Días: hace 2 días Megalink 13 / Jax 0; hoy Jax 16 /
    Megalink 0 → ronda: Jax 16, Megalink 13."""
    await _seed_scored_match()   # hoy: Jax 16, Megalink (user 2) 0
    await _add_round_match(ago=timedelta(days=2), round_number=1, points={1: 0, 2: 13})

    data = (await auth_client.get("/api/matchdays/")).json()
    assert [d["mvps"] for d in data["days"]] == [["Megalink FC"], ["Jax FC"]]
    assert len(data["rounds"]) == 1
    rnd = data["rounds"][0]
    assert [(e["team_name"], e["points"]) for e in rnd["entries"]] == [("Jax FC", 16), ("Megalink FC", 13)]
    assert rnd["mvps"] == ["Jax FC"]
    assert rnd["start"] == data["days"][0]["date"] and rnd["end"] == data["days"][1]["date"]
    assert rnd["complete"] is True


@pytest.mark.asyncio
async def test_matchdays_incomplete_until_all_played_and_scored(auth_client: AsyncClient):
    """`complete` (compartir) exige que TODOS los partidos del día/ronda hayan
    terminado y estén puntuados: un partido de la ronda aún programado la deja
    incompleta (el día de hoy sigue completo); una predicción pendiente también."""
    await _seed_scored_match()
    await _add_round_match(ago=timedelta(days=-1), round_number=1, status=MatchStatus.SCHEDULED)   # mañana, misma ronda

    data = (await auth_client.get("/api/matchdays/")).json()
    assert data["days"][0]["complete"] is True
    assert data["rounds"][0]["complete"] is False

    # Un partido terminado el mismo día pero con una predicción sin puntuar: el día tampoco.
    await _add_round_match(ago=timedelta(hours=3), round_number=1, points={1: 0}, calculated=False)
    data = (await auth_client.get("/api/matchdays/")).json()
    assert data["days"][0]["complete"] is False


@pytest.mark.asyncio
async def test_matchdays_knockout_round_spans_both_legs(auth_client: AsyncClient):
    """En eliminatorias la jornada completa es la fase entera: la ida (martes y
    miércoles de una semana) y la vuelta (la semana siguiente). Suma los puntos de
    ambas y no está completa hasta que se juega (y puntúa) la vuelta."""
    ko = MatchPhase.ROUND_OF_16
    await _add_round_match(ago=timedelta(days=7), phase=ko, points={1: 5})                      # ida: hace una semana
    await _add_round_match(ago=timedelta(0), phase=ko, status=MatchStatus.SCHEDULED)            # vuelta: pendiente

    data = (await auth_client.get("/api/matchdays/")).json()
    assert data["days"][0]["complete"] is True   # el día de la ida sí está completo
    assert len(data["rounds"]) == 1
    rnd = data["rounds"][0]
    assert (rnd["phase"], rnd["round_number"], rnd["complete"]) == ("round_of_16", None, False)
    assert rnd["start"] == data["days"][0]["date"] and rnd["end"] > rnd["start"]

    # Jugada y puntuada la vuelta: una sola jornada completa con la suma de ambas.
    async with TestSessionLocal() as session:
        back = (await session.execute(select(Match).where(Match.api_fixture_id == 7100))).scalar_one()
        back.status = MatchStatus.FINISHED
        session.add(Prediction(user_id=1, match_id=back.id, predicted_home=1, predicted_away=0,
                               points_earned=8, is_calculated=True))
        await session.commit()
    rnd = (await auth_client.get("/api/matchdays/")).json()["rounds"][0]
    assert rnd["complete"] is True
    assert [(e["team_name"], e["points"]) for e in rnd["entries"]] == [("Jax FC", 13)]


@pytest.mark.asyncio
async def test_inactive_user_hidden_from_stats_and_matchdays(auth_client: AsyncClient):
    """Una cuenta desactivada (is_active=False) desaparece de Jornada/MVPs y de
    Aciertos aunque tenga pronósticos puntuados (sus datos se conservan)."""
    await _seed_scored_match()
    async with TestSessionLocal() as session:
        rival = (await session.execute(
            select(User).where(User.team_name == "Megalink FC")
        )).scalar_one()
        rival.is_active = False
        await session.commit()

    day = (await auth_client.get("/api/matchdays/")).json()["days"][0]
    assert [e["team_name"] for e in day["entries"]] == ["Jax FC"]

    stats = (await auth_client.get("/api/stats/")).json()
    assert all(r["team_name"] == "Jax FC" for r in stats["first_goal_ranking"] + stats["exact_ranking"])


@pytest.mark.asyncio
async def test_matchdays_empty(auth_client: AsyncClient):
    data = (await auth_client.get("/api/matchdays/")).json()
    assert data == {"days": [], "rounds": [], "mvp_ranking": []}


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient):
    assert (await client.get("/api/stats/")).status_code == 401


@pytest.mark.asyncio
async def test_matchdays_requires_auth(client: AsyncClient):
    assert (await client.get("/api/matchdays/")).status_code == 401
