"""
Servicio de integración con API-Football para obtener datos de la UCL.
Docs: https://www.api-football.com/documentation-v3
"""
import httpx
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.models.match import MatchPhase, MatchStatus
import logging
import re

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

# Rondas OFICIALES de eliminatoria de API-Football → fase interna. La fase de liga
# se resuelve aparte (por prefijo) porque llega como "League Stage" o "League
# Stage - N" (jornada). Cualquier ronda que no esté aquí ni sea de liga pertenece a
# la FASE PREVIA (clasificación) y se descarta: no forma parte de la quiniela.
ROUND_MAP = {
    "Knockout Round Play-offs": MatchPhase.KNOCKOUT_PLAYOFFS,
    "Round of 16":              MatchPhase.ROUND_OF_16,
    "Quarter-finals":           MatchPhase.QUARTER_FINALS,
    "Semi-finals":              MatchPhase.SEMI_FINALS,
    "Final":                    MatchPhase.FINAL,
}


_LEAGUE_ROUND = re.compile(r"League Stage - (\d+)$")


def _round_number(raw_round: str) -> int | None:
    """Jornada de la fase de liga ('League Stage - N'); None en eliminatorias."""
    m = _LEAGUE_ROUND.search(raw_round)
    return int(m.group(1)) if m else None


def _resolve_phase(raw_round: str) -> MatchPhase | None:
    """Fase interna de una ronda de API-Football; None si es FASE PREVIA (rondas de
    clasificación), que se descarta. La fase de liga llega como 'League Stage' o
    'League Stage - N' (jornada), por eso se resuelve por prefijo."""
    if raw_round.startswith("League Stage"):
        return MatchPhase.LEAGUE
    return ROUND_MAP.get(raw_round)

# Mapeo de status.short de API-Football → MatchStatus interna. El código crudo se
# guarda además en `Match.api_status` (la tarjeta distingue descanso, pausa de la
# prórroga, tanda de penales, suspendido…). Un código desconocido cae en SCHEDULED.
STATUS_MAP = {
    "NS":   MatchStatus.SCHEDULED,  # Not Started
    "TBD":  MatchStatus.SCHEDULED,  # hora por confirmar
    "1H":   MatchStatus.LIVE,
    "HT":   MatchStatus.LIVE,       # descanso (elapsed se queda en 45)
    "2H":   MatchStatus.LIVE,
    "ET":   MatchStatus.LIVE,       # prórroga
    "BT":   MatchStatus.LIVE,       # descanso de la prórroga (elapsed en 105)
    "P":    MatchStatus.LIVE,       # tanda de penales en curso
    "SUSP": MatchStatus.LIVE,       # suspendido con el partido empezado (se reanuda)
    "INT":  MatchStatus.LIVE,       # interrumpido (se reanuda)
    "LIVE": MatchStatus.LIVE,       # en juego, sin detalle de periodo
    "FT":   MatchStatus.FINISHED,
    "AET":  MatchStatus.FINISHED,
    "PEN":  MatchStatus.FINISHED,
    "PST":  MatchStatus.POSTPONED,
    "CANC": MatchStatus.POSTPONED,  # cancelado
    "ABD":  MatchStatus.POSTPONED,  # abandonado (suele reprogramarse)
    "AWD":  MatchStatus.POSTPONED,  # resultado técnico, sin juego
    "WO":   MatchStatus.POSTPONED,  # walkover
}


class ApiFootballError(RuntimeError):
    """API-Football respondió HTTP 200 con `errors` (plan, cuota, parámetros): no hay
    datos válidos. Se lanza en vez de devolver `[]` para que los jobs no confundan el
    fallo con "0 resultados" (p. ej. persistir un ranking vacío sobre uno válido, o
    dar por sincronizados 0 fixtures). La manejan el reintento de `_retry` o el
    salto por elemento (`_fetch_paced`, `gather(return_exceptions=True)`)."""


def _extract_response(data: dict, endpoint: str) -> list[dict]:
    """Extrae 'response' validando el campo 'errors' de API-Football.

    API-Football devuelve HTTP 200 incluso cuando no trae datos por un problema
    de plan, cuota o parámetros: el motivo viaja en 'errors'. En ese caso se lanza
    `ApiFootballError`; devolver `[]` se confundiría con una respuesta válida.
    """
    errors = data.get("errors")
    if errors:  # [] cuando no hay error; dict/lista no vacíos si lo hay.
        raise ApiFootballError(f"API-Football /{endpoint} devolvió errores: {errors}")
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


async def fetch_standings(season: int | None = None) -> list[dict]:
    """Clasificación de la fase de liga (`/standings?league&season`): una fila por
    equipo con `rank`, `team{id,name}` y `all{played,...}`. La API la entrega como
    lista de grupos (tablas); la fase de liga es UNA tabla de 36, pero se aplanan
    todos por robustez."""
    response = await get_client().get(
        f"{BASE_URL}/standings",
        params={
            "league": settings.UCL_LEAGUE_ID,
            "season": season or await resolve_season(),
        },
    )
    response.raise_for_status()
    data = _extract_response(response.json(), "standings")
    groups = ((data[0].get("league") or {}).get("standings") or []) if data else []
    return [row for group in groups for row in group]


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


async def fetch_win_probability(fixture_id: int) -> list[dict]:
    """Pronóstico pre-partido de API-Football (`/predictions?fixture`): probabilidades
    local/empate/visitante, entre otros datos. Una petición por partido."""
    response = await get_client().get(f"{BASE_URL}/predictions", params={"fixture": fixture_id})
    response.raise_for_status()
    return _extract_response(response.json(), "predictions")


async def fetch_absences(season: int | None = None) -> list[dict]:
    """Bajas de TODA la competición en una sola petición (`/injuries?league&season`):
    por partido, los jugadores que se lo pierden o son duda, con el motivo. Incluye los
    partidos ya jugados; quien llama se queda con los que le interesan."""
    response = await get_client().get(
        f"{BASE_URL}/injuries",
        params={
            "league": settings.UCL_LEAGUE_ID,
            "season": season or await resolve_season(),
        },
    )
    response.raise_for_status()
    return _extract_response(response.json(), "injuries")


# Motivos de baja de `/injuries` que NO son una lesión. La API los da en inglés y sin
# catálogo cerrado: lo que no sea sanción ni esté aquí se trata como lesión (rodilla,
# músculo, enfermedad, cirugía...), que es con mucho lo más frecuente.
_SUSPENSION_MARKS = ("card", "suspen")           # "Red Card", "Yellow Cards", "Suspended"
_NOT_INJURY_REASONS = {
    "off the roster", "inactive", "coach's decision", "lacking match fitness",
    "personal reasons", "rest", "transfer negotiations",
}
_NOT_INJURY_MARKS = ("national", "international")   # convocado con su selección


def absence_status(kind: str | None, reason: str | None) -> str:
    """Clasifica una baja de `/injuries` (`type` + `reason`) en lo que muestra el
    selector: "suspended" (sanción por tarjetas), "doubtful" (la API lo da como duda),
    "unavailable" (fuera de la lista, decisión técnica...) o "injured"."""
    text = (reason or "").strip().lower()
    if any(mark in text for mark in _SUSPENSION_MARKS):
        return "suspended"
    if (kind or "").strip().lower() == "questionable":
        return "doubtful"
    if text in _NOT_INJURY_REASONS or any(mark in text for mark in _NOT_INJURY_MARKS):
        return "unavailable"
    return "injured"


def parse_absences(items: list[dict]) -> dict[int, list[dict]]:
    """Agrupa las bajas de `/injuries` por fixture: `api_fixture_id` → lista ordenada
    (equipo, jugador) de {player_id, player, team, status, reason}. La API repite
    entradas del mismo jugador en un partido: se deja una, y si difieren gana la baja
    firme sobre la duda."""
    by_fixture: dict[int, dict[int, dict]] = {}
    for item in items:
        player = item.get("player") or {}
        fixture_id = (item.get("fixture") or {}).get("id")
        if fixture_id is None or player.get("id") is None:
            continue
        absence = {
            "player_id": player["id"],
            "player":    player.get("name"),
            "team":      (item.get("team") or {}).get("name"),
            "status":    absence_status(player.get("type"), player.get("reason")),
            "reason":    player.get("reason"),
        }
        seen = by_fixture.setdefault(fixture_id, {})
        previous = seen.get(absence["player_id"])
        if previous is None or previous["status"] == "doubtful":
            seen[absence["player_id"]] = absence
    return {
        fixture_id: sorted(seen.values(), key=lambda a: (a["team"] or "", a["player"] or "", a["player_id"]))
        for fixture_id, seen in by_fixture.items()
    }


def _percent(value) -> int | None:
    """'45%' → 45; None o ilegible → None."""
    try:
        return int(str(value).rstrip("%").strip())
    except (TypeError, ValueError):
        return None


def parse_win_probability(data: list[dict]) -> dict | None:
    """Probabilidades de `/predictions` → {prob_home, prob_draw, prob_away} (enteros en
    %), o None si la API no las entrega (aún) para ese partido."""
    percent = ((data[0].get("predictions") or {}).get("percent") or {}) if data else {}
    probs = {
        "prob_home": _percent(percent.get("home")),
        "prob_draw": _percent(percent.get("draw")),
        "prob_away": _percent(percent.get("away")),
    }
    return probs if all(v is not None for v in probs.values()) else None


async def fetch_current_team(player_id: int) -> int | None:
    """Club actual de un jugador según su ÚLTIMO traspaso (`/transfers?player`).
    Resuelve al jugador que la API lista en DOS plantillas tras un traspaso (tarda
    en retirarlo del club anterior). None si no hay traspasos registrados."""
    response = await get_client().get(f"{BASE_URL}/transfers", params={"player": player_id})
    response.raise_for_status()
    data = _extract_response(response.json(), "transfers")
    transfers = [t for item in data for t in (item.get("transfers") or []) if t.get("date")]
    if not transfers:
        return None
    latest = max(transfers, key=lambda t: t["date"])   # fechas "YYYY-MM-DD"
    return ((latest.get("teams") or {}).get("in") or {}).get("id")


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


def parse_fixture(fixture_data: dict) -> dict | None:
    """Transforma el formato de API-Football al interno. Devuelve None si el partido
    es de la FASE PREVIA (rondas de clasificación): esos no se guardan, la quiniela
    solo cubre de la fase de liga en adelante."""
    f = fixture_data["fixture"]
    teams = fixture_data["teams"]
    goals = fixture_data["goals"]
    league = fixture_data["league"]
    # Tanda de penales (solo en eliminatorias empatadas): None fuera de ese caso.
    penalty = (fixture_data.get("score") or {}).get("penalty") or {}

    raw_round = league.get("round", "League Stage")
    phase = _resolve_phase(raw_round)
    if phase is None:
        return None  # fase previa: fuera del alcance de la quiniela
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
        "elapsed_extra":    f["status"].get("extra"),   # descuento en curso ("90+3")
        "api_status":       raw_status,                 # detalle: HT, BT, P, SUSP…
        "round_number":     _round_number(raw_round),
        "phase":            phase,
        "status":           status,
        "match_date":       match_date,
    }


def parse_goal_events(events: list[dict]) -> list[dict]:
    """Goles válidos de un partido (normales y de penalti; sin goles en propia ni
    penaltis fallados) en orden cronológico, con goleador y asistente. Se guardan por
    partido (`Match.goal_events`) para calcular goleadores/asistidores de la quiniela
    sin peticiones extra: los eventos ya se descargan para el primer gol."""
    goals: list[dict] = []
    for event in sorted(events, key=lambda e: (e["time"]["elapsed"], e["time"].get("extra") or 0)):
        if event.get("type") != "Goal" or event.get("detail") in ("Missed Penalty", "Own Goal"):
            continue
        player = event.get("player") or {}
        assist = event.get("assist") or {}
        goals.append({
            "player_id": player.get("id"), "player": player.get("name"),
            "assist_id": assist.get("id"), "assist": assist.get("name"),
            "team": (event.get("team") or {}).get("name"),
        })
    return goals


def _card_kind(detail: str | None) -> str:
    """Detalle de una tarjeta de API-Football → "yellow", "second_yellow" o "red". La
    segunda amarilla suele llegar como otra "Yellow Card" seguida de "Red Card", pero a
    veces como "Second Yellow card": se distingue porque no cuenta igual para las
    sanciones (ver services/suspensions.py)."""
    text = (detail or "").lower()
    if "second" in text and "yellow" in text:
        return "second_yellow"
    return "yellow" if "yellow" in text else "red"


def parse_card_events(events: list[dict]) -> list[dict]:
    """Tarjetas de un partido en orden cronológico: {player_id, player, team, card}, con
    `card` = "yellow", "second_yellow" o "red". Se guardan por partido
    (`Match.card_events`) para deducir quién está SANCIONADO en el siguiente (expulsión o
    ciclo de amarillas) sin peticiones extra: los eventos ya se descargan para el primer gol."""
    cards: list[dict] = []
    for event in sorted(events, key=lambda e: (e["time"]["elapsed"], e["time"].get("extra") or 0)):
        if event.get("type") != "Card":
            continue
        player = event.get("player") or {}
        cards.append({
            "player_id": player.get("id"), "player": player.get("name"),
            "team": (event.get("team") or {}).get("name"),
            "card": _card_kind(event.get("detail")),
        })
    return cards


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
