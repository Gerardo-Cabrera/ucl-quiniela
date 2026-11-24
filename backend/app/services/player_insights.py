"""Lo que conviene saber de un jugador antes de elegirlo (selector de primer goleador y
de MVP / máximo goleador): sus goles en la quiniela, si es el máximo goleador de su
equipo y si es baja para un partido (lesionado, sancionado, duda...).

Todo sale de datos ya guardados por los jobs (`Match.goal_events`, `Match.card_events`,
`Match.absences`): ninguna llamada a API-Football dentro del request.
"""
from collections import Counter
from collections.abc import Iterable
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.matches import match_crud
from app.crud.players import player_crud
from app.models.match import Match
from app.models.player import Player
from app.schemas.player import MatchPlayerOut, PlayerFormOut
from app.services.suspensions import suspended_for_match


def goal_tally(goal_events: Iterable[list[dict] | None]) -> Counter[int]:
    """Goles por jugador (`api_player_id`) a partir de los goles guardados por partido."""
    goals: Counter[int] = Counter()
    for events in goal_events:
        goals.update(g["player_id"] for g in events or [] if g.get("player_id") is not None)
    return goals


def team_top_scorers(players: Iterable[Player], goals: Counter[int]) -> set[int]:
    """Ids de los máximos goleadores de cada equipo entre `players`: quien más goles
    lleva en el suyo, con al menos uno (empatados: todos). Regla pura."""
    players = list(players)
    best: dict[str, int] = {}
    for player in players:
        best[player.team_name] = max(best.get(player.team_name, 0), goals[player.api_player_id])
    return {
        player.api_player_id for player in players
        if goals[player.api_player_id] > 0 and goals[player.api_player_id] == best[player.team_name]
    }


async def match_players(db: AsyncSession, match: Match, search: str | None = None) -> list[MatchPlayerOut]:
    """Plantillas de los dos equipos de `match` (cargado con `with_absences=True`),
    cada jugador con sus goles, si es el máximo goleador de su equipo y su
    disponibilidad para ese partido.

    Disponibilidad = bajas de API-Football del partido (`match.absences`) MÁS los
    sancionados que salen de las tarjetas del partido anterior de cada equipo (la API no
    informa de los ciclos de amarillas; ver `services/suspensions.py`). Si un jugador
    figura en ambas, manda la sanción: no puede jugar aunque la API lo dé como duda.
    Por encima de todo, lo que el admin haya corregido a mano (`match.manual_absences`):
    el proveedor tarda en registrar las lesiones recientes, y "available" desmiente una
    baja que no es tal.

    `search` filtra por nombre SIN alterar las marcas: el máximo goleador se decide
    sobre la plantilla completa."""
    teams = [match.home_team, match.away_team]
    squad = await player_crud.get_for_teams(db, teams)
    schedule = await match_crud.get_team_schedules(db, teams)
    goals = goal_tally(row.goal_events for row in schedule)
    top = team_top_scorers(squad, goals)

    unavailable = {a["player_id"]: (a["status"], a["reason"]) for a in match.absences or []}
    for team in teams:
        team_schedule = [row for row in schedule if team in (row.home_team, row.away_team)]
        for player_id, reason in suspended_for_match(team, match.id, team_schedule).items():
            unavailable[player_id] = ("suspended", reason)

    manual = {a["player_id"]: a for a in match.manual_absences or []}
    for player_id, correction in manual.items():
        if correction["status"] == "available":
            unavailable.pop(player_id, None)
        else:
            unavailable[player_id] = (correction["status"], correction.get("reason"))

    if (search or "").strip():
        wanted = {p.api_player_id for p in await player_crud.get_for_teams(db, teams, name_query=search)}
        squad = [p for p in squad if p.api_player_id in wanted]
    result: list[MatchPlayerOut] = []
    for p in squad:
        status, reason = unavailable.get(p.api_player_id, (None, None))
        result.append(MatchPlayerOut(
            api_player_id=p.api_player_id, name=p.name, team_name=p.team_name,
            position=p.position, photo=p.photo,
            goals=goals[p.api_player_id],
            team_top_scorer=p.api_player_id in top,
            availability=status,
            availability_reason=reason,
            availability_manual=p.api_player_id in manual,
        ))
    return result


async def tournament_players(db: AsyncSession) -> list[PlayerFormOut]:
    """Todos los jugadores sincronizados con sus goles en la quiniela y la marca de
    máximo goleador de su equipo (selector de MVP / máximo goleador del torneo)."""
    players = await player_crud.get_all(db)
    goals = goal_tally(await match_crud.get_goal_events(db))
    top = team_top_scorers(players, goals)
    return [
        PlayerFormOut(
            api_player_id=p.api_player_id, name=p.name, team_name=p.team_name,
            position=p.position, photo=p.photo,
            goals=goals[p.api_player_id],
            team_top_scorer=p.api_player_id in top,
        )
        for p in players
    ]
