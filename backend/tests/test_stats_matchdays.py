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
            phase=MatchPhase.LEAGUE, status=MatchStatus.FINISHED,
            match_date=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        session.add(match)
        await session.flush()

        session.add_all([
            # Jax FC (user 1): marcador exacto + primer goleador → 11 pts
            Prediction(user_id=1, match_id=match.id, predicted_home=2, predicted_away=1,
                       first_goal_player_id=10, first_goal_player="Vinicius Jr",
                       points_earned=11, is_calculated=True),
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
    assert day["mvp_points"] == 11
    assert day["mvps"] == ["Jax FC"]
    # Ambos participantes aparecen, ordenados por puntos desc.
    assert [e["team_name"] for e in day["entries"]] == ["Jax FC", "Megalink FC"]

    assert data["mvp_ranking"] == [{"team_name": "Jax FC", "count": 1}]


@pytest.mark.asyncio
async def test_matchdays_empty(auth_client: AsyncClient):
    data = (await auth_client.get("/api/matchdays/")).json()
    assert data == {"days": [], "mvp_ranking": []}


@pytest.mark.asyncio
async def test_stats_requires_auth(client: AsyncClient):
    assert (await client.get("/api/stats/")).status_code == 401


@pytest.mark.asyncio
async def test_matchdays_requires_auth(client: AsyncClient):
    assert (await client.get("/api/matchdays/")).status_code == 401
