"""
Integration tests para los endpoints de la API.
Usa SQLite en memoria vía conftest fixtures.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.models.match import Match, MatchPhase, MatchStatus
from tests.conftest import TestSessionLocal


# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """El nombre de equipo es texto libre; el alias es opcional (null si no se envía)."""
    resp = await client.post("/api/auth/register", json={
        "team_name": "Cualquier Nombre FC",
        "email": "new@test.com",
        "password": "pass1234",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["team_name"] == "Cualquier Nombre FC"
    assert data["email"] == "new@test.com"
    assert data["alias"] is None
    assert data["is_admin"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_register_with_alias(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Equipo Alias FC",
        "email": "alias@test.com",
        "password": "pass1234",
        "alias": "elcapo",
    })
    assert resp.status_code == 201
    assert resp.json()["alias"] == "elcapo"


@pytest.mark.asyncio
async def test_register_blank_alias_is_null(client: AsyncClient):
    """Un alias en blanco se normaliza a null (no cuenta como alias)."""
    resp = await client.post("/api/auth/register", json={
        "team_name": "Sin Alias FC",
        "email": "blank@test.com",
        "password": "pass1234",
        "alias": "   ",
    })
    assert resp.status_code == 201
    assert resp.json()["alias"] is None


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"team_name": "Equipo A", "email": "dup@test.com", "password": "pass1234"}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 201
    resp2 = await client.post("/api/auth/register", json={**payload, "team_name": "Equipo B"})
    assert resp2.status_code == 409
    assert "email" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_team_name(client: AsyncClient):
    payload = {"team_name": "Mismo Equipo", "email": "t1@test.com", "password": "pass1234"}
    assert (await client.post("/api/auth/register", json=payload)).status_code == 201
    resp2 = await client.post("/api/auth/register", json={**payload, "email": "t2@test.com"})
    assert resp2.status_code == 409
    assert "equipo" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_alias(client: AsyncClient):
    p1 = {"team_name": "Equipo Uno", "email": "a1@test.com", "password": "pass1234", "alias": "duplialias"}
    assert (await client.post("/api/auth/register", json=p1)).status_code == 201
    p2 = {"team_name": "Equipo Dos", "email": "a2@test.com", "password": "pass1234", "alias": "duplialias"}
    resp2 = await client.post("/api/auth/register", json=p2)
    assert resp2.status_code == 409
    assert "alias" in resp2.json()["detail"].lower()


async def _register(client: AsyncClient, **over):
    payload = {"team_name": "Login Team", "email": "login@test.com", "password": "pass1234", "alias": "loginalias"}
    payload.update(over)
    return await client.post("/api/auth/register", json=payload)


@pytest.mark.asyncio
async def test_login_by_email(client: AsyncClient):
    await _register(client)
    resp = await client.post("/api/auth/login", json={"identifier": "login@test.com", "password": "pass1234"})
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "login@test.com"


@pytest.mark.asyncio
async def test_login_by_alias(client: AsyncClient):
    await _register(client)
    resp = await client.post("/api/auth/login", json={"identifier": "loginalias", "password": "pass1234"})
    assert resp.status_code == 200
    assert resp.json()["user"]["alias"] == "loginalias"


@pytest.mark.asyncio
async def test_login_by_team_name(client: AsyncClient):
    await _register(client)
    resp = await client.post("/api/auth/login", json={"identifier": "Login Team", "password": "pass1234"})
    assert resp.status_code == 200
    assert resp.json()["user"]["team_name"] == "Login Team"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await _register(client, email="wrong@test.com", team_name="Wrong Team", alias="wrongalias")
    resp = await client.post("/api/auth/login", json={"identifier": "wrong@test.com", "password": "incorrectpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Short FC",
        "email": "short@test.com",
        "password": "abc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "identifier": "ghost@test.com",
        "password": "anything",
    })
    assert resp.status_code == 401


# ── VALIDACIONES DE REGISTRO ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_short_team_name(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "ab", "email": "st@test.com", "password": "pass1234"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_alias(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Equipo Valido", "email": "sa@test.com", "password": "pass1234", "alias": "ab"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_password_min_6(client: AsyncClient):
    r5 = await client.post("/api/auth/register", json={
        "team_name": "Pass Cinco", "email": "p5@test.com", "password": "12345"})
    assert r5.status_code == 422
    r6 = await client.post("/api/auth/register", json={
        "team_name": "Pass Seis", "email": "p6@test.com", "password": "123456"})
    assert r6.status_code == 201


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Email Malo", "email": "no-es-un-email", "password": "pass1234"})
    assert resp.status_code == 422


# ── CAMBIO / RECUPERACIÓN DE CONTRASEÑA ──────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_success(auth_client: AsyncClient):
    """El usuario autenticado cambia su contraseña; la nueva vale y la vieja no."""
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "testpass123", "new_password": "nuevapass456"})
    assert resp.status_code == 200
    assert (await auth_client.post("/api/auth/login", json={
        "identifier": "test@test.com", "password": "nuevapass456"})).status_code == 200
    assert (await auth_client.post("/api/auth/login", json={
        "identifier": "test@test.com", "password": "testpass123"})).status_code == 401


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "incorrecta", "new_password": "nuevapass456"})
    assert resp.status_code == 400
    assert "actual" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_same_as_current(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "testpass123", "new_password": "testpass123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    resp = await client.post("/api/auth/change-password", json={
        "current_password": "x", "new_password": "nuevapass456"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_short_new(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "testpass123", "new_password": "123"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient):
    """Recuperación sin email: email + nombre de equipo correctos → nueva contraseña."""
    await client.post("/api/auth/register", json={
        "team_name": "Reset FC", "email": "reset@test.com", "password": "origpass1"})
    resp = await client.post("/api/auth/reset-password", json={
        "email": "reset@test.com", "team_name": "Reset FC", "new_password": "flamante99"})
    assert resp.status_code == 204
    assert (await client.post("/api/auth/login", json={
        "identifier": "reset@test.com", "password": "flamante99"})).status_code == 200
    assert (await client.post("/api/auth/login", json={
        "identifier": "reset@test.com", "password": "origpass1"})).status_code == 401


@pytest.mark.asyncio
async def test_reset_password_wrong_data(client: AsyncClient):
    """Si el email y el equipo no son del mismo usuario, no se restablece."""
    await client.post("/api/auth/register", json={
        "team_name": "Real FC", "email": "real@test.com", "password": "origpass1"})
    resp = await client.post("/api/auth/reset-password", json={
        "email": "real@test.com", "team_name": "Equipo Falso", "new_password": "flamante99"})
    assert resp.status_code == 400
    assert "no coinciden" in resp.json()["detail"]
    # La contraseña original sigue siendo válida.
    assert (await client.post("/api/auth/login", json={
        "identifier": "real@test.com", "password": "origpass1"})).status_code == 200


@pytest.mark.asyncio
async def test_reset_password_short_new(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "team_name": "Short FC", "email": "short@test.com", "password": "origpass1"})
    resp = await client.post("/api/auth/reset-password", json={
        "email": "short@test.com", "team_name": "Short FC", "new_password": "123"})
    assert resp.status_code == 422


# ── PERFIL: alias opcional ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_alias_success(auth_client: AsyncClient):
    """Estando logueado, se puede fijar el alias y luego iniciar sesión con él."""
    resp = await auth_client.patch("/api/auth/me", json={"alias": "ElCapo"})
    assert resp.status_code == 200
    assert resp.json()["alias"] == "ElCapo"
    assert (await auth_client.post("/api/auth/login", json={
        "identifier": "ElCapo", "password": "testpass123"})).status_code == 200


@pytest.mark.asyncio
async def test_update_alias_clear(auth_client: AsyncClient):
    """El alias es opcional: enviarlo en blanco lo quita (None)."""
    await auth_client.patch("/api/auth/me", json={"alias": "TempAlias"})
    resp = await auth_client.patch("/api/auth/me", json={"alias": ""})
    assert resp.status_code == 200
    assert resp.json()["alias"] is None


@pytest.mark.asyncio
async def test_update_alias_too_short(auth_client: AsyncClient):
    resp = await auth_client.patch("/api/auth/me", json={"alias": "ab"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_alias_conflict(auth_client: AsyncClient):
    """No se puede tomar un alias que ya usa otro usuario."""
    await auth_client.post("/api/auth/register", json={
        "team_name": "Otro FC", "email": "otro@test.com", "password": "pass1234", "alias": "Tomado"})
    resp = await auth_client.patch("/api/auth/me", json={"alias": "Tomado"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_profile_requires_auth(client: AsyncClient):
    assert (await client.patch("/api/auth/me", json={"alias": "X"})).status_code == 401


@pytest.mark.asyncio
async def test_config_teams_from_db(client: AsyncClient):
    """El selector del Top 8 lee los clubes de la BD (sincronizados desde la API)."""
    resp = await client.get("/api/config/teams")
    assert resp.status_code == 200
    body = resp.json()
    assert "allowed_teams" not in body
    assert "Real Madrid" in body["ucl_teams"]


# ── PROTECTED ENDPOINTS (unauthorized) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_matches_requires_auth(client: AsyncClient):
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_requires_auth(client: AsyncClient):
    resp = await client.get("/api/predictions/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_requires_auth(client: AsyncClient):
    resp = await client.get("/api/leaderboard/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_top8_requires_auth(client: AsyncClient):
    resp = await client.get("/api/top8/me")
    assert resp.status_code == 401


# ── PROTECTED ENDPOINTS (authenticated) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_matches_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/matches/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_predictions_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/predictions/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_leaderboard(auth_client: AsyncClient):
    resp = await auth_client.get("/api/leaderboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["team_name"] == "Jax FC"


@pytest.mark.asyncio
async def test_leaderboard_ties_share_rank(auth_client: AsyncClient):
    """Empatados comparten rank (1, 2, 2, ...) en orden alfabético determinista."""
    from app.models.prediction import Prediction

    for team, email in [("Genkidama F.C", "g@test.com"), ("Megalink FC", "m@test.com")]:
        resp = await auth_client.post("/api/auth/register", json={
            "team_name": team, "email": email, "password": "pass1234",
        })
        assert resp.status_code == 201

    # Solo Jax FC (user 1) suma puntos; los otros dos empatan en 0.
    match_id = await _create_match()
    async with TestSessionLocal() as session:
        session.add(Prediction(
            user_id=1, match_id=match_id,
            predicted_home=1, predicted_away=0,
            points_earned=5, is_calculated=True,
        ))
        await session.commit()

    data = (await auth_client.get("/api/leaderboard/")).json()
    assert [(e["team_name"], e["rank"], e["total_points"]) for e in data] == [
        ("Jax FC", 1, 5),
        ("Genkidama F.C", 2, 0),
        ("Megalink FC", 2, 0),
    ]


@pytest.mark.asyncio
async def test_top8_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/top8/me")
    assert resp.status_code == 200
    assert resp.json() == []


VALID_TOP8 = [
    "Real Madrid", "Manchester City", "Bayern Munich", "Barcelona",
    "Arsenal", "Liverpool", "Inter Milan", "Paris Saint-Germain",
]


def _picks_payload(teams: list[str]) -> dict:
    return {
        "picks": [
            {"position": i, "team_name": team}
            for i, team in enumerate(teams, start=1)
        ]
    }


@pytest.mark.asyncio
async def test_top8_save_and_retrieve(auth_client: AsyncClient):
    resp = await auth_client.post("/api/top8/", json=_picks_payload(VALID_TOP8))
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 8

    resp2 = await auth_client.get("/api/top8/me")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 8


@pytest.mark.asyncio
async def test_top8_invalid_count(auth_client: AsyncClient):
    picks = {
        "picks": [
            {"position": 1, "team_name": "Real Madrid"},
            {"position": 2, "team_name": "Barcelona"},
        ]
    }
    resp = await auth_client.post("/api/top8/", json=picks)
    assert resp.status_code == 400
    assert "exactamente 8" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_top8_rejects_unknown_team(auth_client: AsyncClient):
    teams = VALID_TOP8[:7] + ["Equipo Inventado"]
    resp = await auth_client.post("/api/top8/", json=_picks_payload(teams))
    assert resp.status_code == 400
    assert "no válidos" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_top8_rejects_duplicate_team(auth_client: AsyncClient):
    teams = VALID_TOP8[:7] + ["Real Madrid"]  # Real Madrid repetido
    resp = await auth_client.post("/api/top8/", json=_picks_payload(teams))
    assert resp.status_code == 400
    assert "repetir" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_top8_locked_after_season_start(auth_client: AsyncClient):
    """El Top 8 se fija al arrancar la temporada: con el primer partido ya en juego,
    guardar se rechaza."""
    async with TestSessionLocal() as session:
        session.add(Match(
            api_fixture_id=7777, home_team="Real Madrid", away_team="Barcelona",
            phase=MatchPhase.LEAGUE, status=MatchStatus.LIVE,
            match_date=datetime.now(timezone.utc) - timedelta(minutes=5),
        ))
        await session.commit()

    resp = await auth_client.post("/api/top8/", json=_picks_payload(VALID_TOP8))
    assert resp.status_code == 400
    assert "antes del primer partido" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_top8_calculate_requires_admin(auth_client: AsyncClient):
    resp = await auth_client.post("/api/top8/calculate", json={"actual_top8": VALID_TOP8})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_top8_calculate_scores_picks(admin_client: AsyncClient):
    # Guardar picks: posiciones 1-7 correctas, octavo equipo fuera del top8 real.
    my_teams = VALID_TOP8[:7] + ["Juventus"]
    resp = await admin_client.post("/api/top8/", json=_picks_payload(my_teams))
    assert resp.status_code == 201

    resp = await admin_client.post("/api/top8/calculate", json={"actual_top8": VALID_TOP8})
    assert resp.status_code == 200
    assert resp.json()["picks_calculated"] == 8

    picks = (await admin_client.get("/api/top8/me")).json()
    assert all(p["is_calculated"] for p in picks)
    # 7 aciertos exactos (5 pts) + 1 fallo (0 pts) = 35
    assert sum(p["points_earned"] for p in picks) == 35

    # Una vez calculado, el Top 8 queda bloqueado.
    resp = await admin_client.post("/api/top8/", json=_picks_payload(VALID_TOP8))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_top8_calculate_rejects_invalid_teams(admin_client: AsyncClient):
    bad = VALID_TOP8[:7] + ["Equipo Falso"]
    resp = await admin_client.post("/api/top8/calculate", json={"actual_top8": bad})
    assert resp.status_code == 400


# ── PREDICTIONS VALIDATION ────────────────────────────────────────────────────


async def _create_match(**overrides) -> int:
    """Inserta un partido de prueba directamente en la BD y retorna su id."""
    defaults = dict(
        api_fixture_id=1001,
        home_team="Real Madrid",
        away_team="Barcelona",
        phase=MatchPhase.LEAGUE,
        status=MatchStatus.SCHEDULED,
        match_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    defaults.update(overrides)
    async with TestSessionLocal() as session:
        match = Match(**defaults)
        session.add(match)
        await session.commit()
        await session.refresh(match)
        return match.id


@pytest.mark.asyncio
async def test_prediction_rejects_negative_score(auth_client: AsyncClient):
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": 1,
        "predicted_home": -1,
        "predicted_away": 0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_rejects_absurd_score(auth_client: AsyncClient):
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": 1,
        "predicted_home": 99,
        "predicted_away": 0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_create_success(auth_client: AsyncClient):
    match_id = await _create_match()
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 2,
        "predicted_away": 1,
        "first_goal_player_id": 10,  # Vinicius Jr (Real Madrid), sembrado en conftest
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["predicted_home"] == 2
    assert data["first_goal_player_id"] == 10
    assert data["first_goal_player"] == "Vinicius Jr"
    assert data["is_calculated"] is False


@pytest.mark.asyncio
async def test_prediction_rejects_started_match(auth_client: AsyncClient):
    """El status puede seguir SCHEDULED entre syncs: la fecha manda."""
    match_id = await _create_match(
        match_date=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
    })
    assert resp.status_code == 400
    assert "comenzó" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_prediction_rejects_finished_match(auth_client: AsyncClient):
    match_id = await _create_match(
        status=MatchStatus.FINISHED,
        match_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_prediction_rejects_foreign_first_goal_player(auth_client: AsyncClient):
    """El goleador pronosticado debe jugar en uno de los dos equipos del partido."""
    match_id = await _create_match()  # Real Madrid vs Barcelona
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
        "first_goal_player_id": 99999,  # no existe en plantillas
    })
    assert resp.status_code == 400
    assert "no pertenece" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_prediction_get_match_players(auth_client: AsyncClient):
    """El endpoint de plantillas devuelve los jugadores de ambos equipos."""
    match_id = await _create_match()
    resp = await auth_client.get(f"/api/matches/{match_id}/players")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    # 2 de Real Madrid + 2 de Barcelona sembrados en conftest.
    assert {"Vinicius Jr", "Lewandowski"} <= names
    assert len(resp.json()) == 4


# ── HEALTH ENDPOINTS ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
