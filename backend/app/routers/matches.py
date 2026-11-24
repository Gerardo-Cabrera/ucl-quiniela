from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.match import MatchPhase, MatchStatus
from app.models.user import User
from app.schemas import MatchOut, MatchPlayerOut, ManualAvailabilityUpdate
from app.core.deps import get_current_user, get_admin_user
from app.core.rate_limit import limiter
from app.config import settings
from app.services.scheduler import (
    sync_ucl_fixtures, sync_players, players_sync_in_progress, sync_win_probabilities,
    sync_absences,
)
from app.services.prediction_window import annotate_predictable
from app.services.player_insights import match_players
from app.crud import match_crud, player_crud

router = APIRouter(prefix="/matches", tags=["Matches"])

_TOURNAMENT_TZ = settings.tournament_tz


@router.get("/", response_model=list[MatchOut])
async def get_matches(
    phase: MatchPhase | None = None,
    status: MatchStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    matches = await match_crud.get_all(db, phase=phase, status=status)
    # Sin filtros la lista es completa (lo que pide el frontend, cada minuto): el primer
    # partido de cada día sale de ella y se ahorra una consulta.
    await annotate_predictable(
        db, matches, _TOURNAMENT_TZ, complete=phase is None and status is None
    )
    return matches


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    match = await match_crud.get_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    await annotate_predictable(db, [match], _TOURNAMENT_TZ)
    return match


@router.get("/{match_id}/players", response_model=list[MatchPlayerOut])
async def get_match_players(
    match_id: int,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Plantillas de los dos equipos del partido, para elegir el primer goleador. Cada
    jugador trae lo que ayuda a decidir: goles en la quiniela (`goals`), si es el máximo
    goleador de su equipo (`team_top_scorer`) y si es baja o duda para ESTE partido
    (`availability`: injured / suspended / doubtful / unavailable, con su motivo; la
    sanción incluye los ciclos de amarillas). `?search=` filtra por subcadena del nombre (literal,
    sin distinguir mayúsculas): sirve para obtener el id de un goleador para el backfill
    admin. Vacío si aún no se han sincronizado las plantillas."""
    match = await match_crud.get_by_id(db, match_id, with_absences=True)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    return await match_players(db, match, search)


async def _match_and_player(db: AsyncSession, match_id: int, player_id: int):
    """Partido (con sus bajas cargadas y la fila BLOQUEADA hasta el commit, para que dos
    correcciones simultáneas no se pisen) y jugador de una corrección manual; el jugador
    debe pertenecer a uno de los dos equipos del partido."""
    match = await match_crud.get_by_id(db, match_id, with_absences=True, for_update=True)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    player = await player_crud.get_by_api_id(db, player_id)
    if player is None or player.team_name not in (match.home_team, match.away_team):
        raise HTTPException(
            status_code=400,
            detail=f"El jugador {player_id} no pertenece a {match.home_team} ni {match.away_team}.",
        )
    return match, player


@router.put(
    "/{match_id}/players/{player_id}/availability",
    response_model=list[MatchPlayerOut],
    summary="Admin: corregir a mano la disponibilidad de un jugador",
)
async def set_player_availability(
    match_id: int,
    player_id: int,
    data: ManualAvailabilityUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Fija a mano el estado de un jugador para ESTE partido: una baja (lesionado,
    sancionado, duda, no disponible) que el proveedor aún no ha registrado, o
    `available` para desmentir la que digan la API o las tarjetas. Manda sobre los datos
    automáticos y el job de bajas no la pisa; se quita con DELETE. Devuelve las plantillas
    del partido ya actualizadas."""
    match, player = await _match_and_player(db, match_id, player_id)
    await match_crud.set_manual_absence(db, match, player_id, {
        "player_id": player.api_player_id, "player": player.name, "team": player.team_name,
        "status": data.status, "reason": data.reason,
    })
    return await match_players(db, match)


@router.delete(
    "/{match_id}/players/{player_id}/availability",
    response_model=list[MatchPlayerOut],
    summary="Admin: quitar la corrección manual de un jugador",
)
async def clear_player_availability(
    match_id: int,
    player_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Quita la corrección manual: el jugador vuelve a mostrar lo que digan la API y las
    tarjetas. Devuelve las plantillas del partido ya actualizadas."""
    match, _player = await _match_and_player(db, match_id, player_id)
    await match_crud.set_manual_absence(db, match, player_id, None)
    return await match_players(db, match)


@router.post("/sync", status_code=202, summary="Admin: Forzar sync con API-Football")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync(
    request: Request,
    background_tasks: BackgroundTasks,
    _: User = Depends(get_admin_user),
):
    """Endpoint admin para forzar sincronización manual (en background)."""
    background_tasks.add_task(sync_ucl_fixtures)
    return {"message": "Sincronización iniciada."}


@router.post("/sync-squads", status_code=202, summary="Admin: Forzar sync de plantillas")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync_squads(
    request: Request,
    background_tasks: BackgroundTasks,
    _: User = Depends(get_admin_user),
):
    """Sincroniza en background las plantillas de los equipos vivos (una petición por
    equipo, espaciadas): para forzarlo tras un mercado de fichajes sin esperar al job.
    409 si ya hay una corrida en curso (una sola a la vez, también frente al job)."""
    if players_sync_in_progress():
        raise HTTPException(status_code=409, detail="Ya hay una sincronización de plantillas en curso.")
    background_tasks.add_task(sync_players)
    return {"message": "Sincronización de plantillas iniciada."}


@router.post("/sync-probabilities", status_code=202, summary="Admin: Forzar sync de probabilidades")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync_probabilities(
    request: Request,
    background_tasks: BackgroundTasks,
    force: bool = False,
    _: User = Depends(get_admin_user),
):
    """Actualiza en background la probabilidad de victoria del próximo partido de cada
    equipo (una petición por partido, espaciadas). Por defecto solo pide las vencidas
    (SYNC_PROBABILITIES_HOURS); con `?force=true` las pide todas."""
    background_tasks.add_task(sync_win_probabilities, force)
    return {"message": "Sincronización de probabilidades iniciada."}



@router.post("/sync-absences", status_code=202, summary="Admin: Forzar sync de bajas")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync_absences(
    request: Request,
    background_tasks: BackgroundTasks,
    _: User = Depends(get_admin_user),
):
    """Actualiza en background las bajas (lesionados, sancionados, dudas) de los partidos
    por jugar: una sola petición a API-Football. Para refrescarlas antes del cierre de
    una jornada sin esperar al job (cada SYNC_ABSENCES_HOURS)."""
    background_tasks.add_task(sync_absences)
    return {"message": "Sincronización de bajas iniciada."}
