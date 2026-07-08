"""
Servicio de integración con API-Football para obtener datos de la UCL.
Docs: https://www.api-football.com/documentation-v3
"""
import httpx
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.models.match import MatchPhase, MatchStatus
import logging

logger = logging.getLogger(__name__)

BASE_URL = settings.football_base_url

# Cliente compartido para reutilizar conexiones (lazy init).
_client: httpx.AsyncClient | None = None
# Temporada resuelta por la API cuando UCL_SEASON=0 (cache en proceso).
_resolved_season: int | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=settings.football_headers,
            timeout=settings.API_FOOTBALL_TIMEOUT,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None

# Mapeo de rondas de API-Football → MatchPhase interna
ROUND_MAP = {
    "League Stage":             MatchPhase.LEAGUE,
    "Knockout Round Play-offs": MatchPhase.KNOCKOUT_PLAYOFFS,
    "Round of 16":              MatchPhase.ROUND_OF_16,
    "Quarter-finals":           MatchPhase.QUARTER_FINALS,
    "Semi-finals":              MatchPhase.SEMI_FINALS,
    "Final":                    MatchPhase.FINAL,
}

# Mapeo de status de API-Football → MatchStatus interna
STATUS_MAP = {
    "NS":  MatchStatus.SCHEDULED,   # Not Started
    "1H":  MatchStatus.LIVE,
    "HT":  MatchStatus.LIVE,
    "2H":  MatchStatus.LIVE,
    "ET":  MatchStatus.LIVE,
    "P":   MatchStatus.LIVE,
    "FT":  MatchStatus.FINISHED,
    "AET": MatchStatus.FINISHED,
    "PEN": MatchStatus.FINISHED,
    "PST": MatchStatus.POSTPONED,
}


def _extract_response(data: dict, endpoint: str) -> list[dict]:
    """Extrae 'response' validando el campo 'errors' de API-Football.

    API-Football devuelve HTTP 200 incluso cuando no trae datos por un problema
    de plan, cuota o parámetros: el motivo viaja en 'errors'. Sin esto, esos
    casos se verían como "0 resultados" sin explicación en los logs.
    """
    errors = data.get("errors")
    if errors:  # [] cuando no hay error; dict/lista no vacíos si lo hay.
        logger.warning("API-Football /%s devolvió errores: %s", endpoint, errors)
    return data.get("response", [])


async def fetch_current_season() -> int:
    """Identifica la temporada de la competición vía API: la marcada como `current`
    en `/leagues?id=<UCL_LEAGUE_ID>` (o la más reciente como respaldo)."""
    response = await get_client().get(
        f"{BASE_URL}/leagues", params={"id": settings.UCL_LEAGUE_ID}
    )
    response.raise_for_status()
    data = _extract_response(response.json(), "leagues")
    seasons = data[0].get("seasons", []) if data else []
    for s in seasons:
        if s.get("current"):
            return s["year"]
    return seasons[-1]["year"] if seasons else settings.UCL_SEASON


async def resolve_season() -> int:
    """Temporada a consultar: la configurada (`UCL_SEASON` > 0) o, si es 0, la que
    la API marca como actual. Se cachea para no repetir la llamada."""
    global _resolved_season
    if settings.UCL_SEASON:
        return settings.UCL_SEASON
    if _resolved_season is None:
        _resolved_season = await fetch_current_season()
        logger.info("Temporada identificada automáticamente: %s", _resolved_season)
    return _resolved_season


async def fetch_fixtures(season: int | None = None) -> list[dict]:
    """
    Obtiene todos los fixtures de UCL para la temporada indicada.
    """
    response = await get_client().get(
        f"{BASE_URL}/fixtures",
        params={
            "league": settings.UCL_LEAGUE_ID,
            "season": season or await resolve_season(),
        },
    )
    response.raise_for_status()
    return _extract_response(response.json(), "fixtures")


async def fetch_teams(season: int | None = None) -> list[dict]:
    """Obtiene los clubes participantes de la UCL para la temporada indicada."""
    response = await get_client().get(
        f"{BASE_URL}/teams",
        params={
            "league": settings.UCL_LEAGUE_ID,
            "season": season or await resolve_season(),
        },
    )
    response.raise_for_status()
    return _extract_response(response.json(), "teams")


def parse_team(team_data: dict) -> dict:
    """Transforma una entrada de `/teams` en una fila de la tabla `teams`."""
    t = team_data["team"]
    return {
        "api_team_id": t["id"],
        "name":        t["name"],
        "code":        t.get("code"),
        "country":     t.get("country"),
        "logo":        t.get("logo"),
    }


async def fetch_fixture_events(fixture_id: int) -> list[dict]:
    """
    Obtiene los eventos de un partido (goles, tarjetas, etc.)
    para determinar el primer gol.
    """
    response = await get_client().get(
        f"{BASE_URL}/fixtures/events",
        params={"fixture": fixture_id},
    )
    response.raise_for_status()
    return _extract_response(response.json(), "fixtures/events")


async def fetch_squad(team_api_id: int) -> list[dict]:
    """
    Obtiene la plantilla (squad) de un equipo desde `/players/squads`.
    """
    response = await get_client().get(
        f"{BASE_URL}/players/squads",
        params={"team": team_api_id},
    )
    response.raise_for_status()
    return _extract_response(response.json(), "players/squads")


def parse_squad(squad_data: dict) -> list[dict]:
    """Transforma una entrada de `/players/squads` en filas de la tabla `players`.

    Estructura de entrada: {"team": {id, name}, "players": [{id, name, position, photo}]}.
    """
    team = squad_data["team"]
    team_api_id = team["id"]
    team_name = team["name"]
    parsed: list[dict] = []
    for p in squad_data.get("players", []):
        if p.get("id") is None:
            continue
        parsed.append({
            "api_player_id": p["id"],
            "name":          p.get("name") or f"#{p['id']}",
            "team_api_id":   team_api_id,
            "team_name":     team_name,
            "position":      p.get("position"),
            "photo":         p.get("photo"),
        })
    return parsed


def parse_fixture(fixture_data: dict) -> dict:
    """
    Transforma el formato de API-Football al formato interno.
    """
    f = fixture_data["fixture"]
    teams = fixture_data["teams"]
    goals = fixture_data["goals"]
    league = fixture_data["league"]
    # Tanda de penales (solo en eliminatorias empatadas): None fuera de ese caso.
    penalty = (fixture_data.get("score") or {}).get("penalty") or {}

    raw_round  = league.get("round", "League Stage")
    phase      = ROUND_MAP.get(raw_round, MatchPhase.LEAGUE)
    if raw_round not in ROUND_MAP:
        logger.warning("Ronda desconocida de API-Football: %r (usando LEAGUE)", raw_round)
    raw_status = f["status"]["short"]
    status     = STATUS_MAP.get(raw_status, MatchStatus.SCHEDULED)
    match_date = datetime.fromisoformat(f["date"])

    # Fallback de finalización: un partido de fase de liga aún LIVE pasados
    # MATCH_FINISH_FALLBACK_MINUTES del kickoff se da por finalizado. Las
    # eliminatorias pueden ir a prórroga/penales, así que ahí se respeta la API.
    if (
        status == MatchStatus.LIVE
        and phase == MatchPhase.LEAGUE
        and datetime.now(timezone.utc) - match_date
            > timedelta(minutes=settings.MATCH_FINISH_FALLBACK_MINUTES)
    ):
        status = MatchStatus.FINISHED

    return {
        "api_fixture_id":   f["id"],
        "home_team":        teams["home"]["name"],
        "away_team":        teams["away"]["name"],
        "home_team_api_id": teams["home"]["id"],
        "away_team_api_id": teams["away"]["id"],
        "home_team_logo":   teams["home"]["logo"],
        "away_team_logo":   teams["away"]["logo"],
        "home_score":       goals["home"],
        "away_score":       goals["away"],
        "penalty_home":     penalty.get("home"),
        "penalty_away":     penalty.get("away"),
        "elapsed":          f["status"].get("elapsed"),
        "phase":            phase,
        "status":           status,
        "match_date":       match_date,
    }


def get_first_goal_scorer(events: list[dict]) -> dict | None:
    """
    Determina quién anotó el primer gol a partir de los eventos del partido.
    Devuelve {"team", "player_id", "player_name"} o None si no hubo gol.

    El `player_id` es el id de API-Football del goleador: el mismo namespace que
    la tabla `players`, de modo que el primer gol se puntúa por id.
    """
    for event in sorted(events, key=lambda e: (e["time"]["elapsed"], e["time"].get("extra") or 0)):
        if event["type"] == "Goal" and event["detail"] != "Missed Penalty":
            player = event.get("player") or {}
            return {
                "team":        event["team"]["name"],
                "player_id":   player.get("id"),
                "player_name": player.get("name"),
            }
    return None
