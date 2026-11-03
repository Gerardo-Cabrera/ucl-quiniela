from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas import (
    PredictionCreate, PredictionOut, PredictionOverrideUpdate, PredictionOverrideOut,
    PredictionBackfillItem, PredictionBackfillRequest,
)
from app.core.deps import get_current_user, get_admin_user
from app.crud import prediction_crud, match_crud, player_crud, app_state_crud, user_crud
from app.services.prediction_window import ensure_predictable, annotate_predictable
from app.services.scheduler import sync_first_goals, calculate_pending_points

router = APIRouter(prefix="/predictions", tags=["Predictions"])

_TOURNAMENT_TZ = settings.tournament_tz


async def _validate_first_goal_player(
    db: AsyncSession, match: Match, player_id: int | None
) -> tuple[int | None, str | None]:
    """Valida el pronóstico de primer goleador: el jugador debe existir y jugar
    en uno de los dos equipos del partido. Devuelve (api_player_id, nombre) para
    persistir, o (None, None) si no se pronostica."""
    if player_id is None:
        return None, None
    player = await player_crud.get_by_api_id(db, player_id)
    if player is None or player.team_name not in (match.home_team, match.away_team):
        raise HTTPException(
            status_code=400,
            detail=f"El jugador {player_id} no pertenece a {match.home_team} ni {match.away_team}.",
        )
    return player.api_player_id, player.name


@router.get("/", response_model=list[PredictionOut])
async def get_my_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    predictions = await prediction_crud.get_by_user(db, current_user.id)
    await annotate_predictable(db, [p.match for p in predictions], _TOURNAMENT_TZ)
    return predictions


@router.get("/user/{user_id}", response_model=list[PredictionOut])
async def get_user_predictions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Pronósticos de otro participante, revelados por jornada: solo los de partidos
    cuya jornada (día) ya arrancó (su primer partido). Las jornadas por empezar no
    se muestran, así nadie ve pronósticos de partidos que aún no comienzan."""
    visible = await match_crud.started_day_match_ids(db, _TOURNAMENT_TZ)
    return await prediction_crud.get_by_user(db, user_id, only_match_ids=visible)


@router.get("/override", response_model=PredictionOverrideOut, summary="Admin: estado de la prórroga de pronósticos")
async def get_prediction_override(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    enabled = await app_state_crud.get_prediction_override(db)
    return PredictionOverrideOut(enabled=enabled, lead_minutes=settings.PREDICTION_LEAD_MINUTES)


@router.put("/override", response_model=PredictionOverrideOut, summary="Admin: activar/desactivar la prórroga")
async def set_prediction_override(
    data: PredictionOverrideUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Interruptor global: con la prórroga activa los pronósticos de una jornada
    siguen abiertos desde que vence el plazo normal hasta que arranca su primer partido."""
    await app_state_crud.set_prediction_override(db, data.enabled)
    return PredictionOverrideOut(enabled=data.enabled, lead_minutes=settings.PREDICTION_LEAD_MINUTES)


@router.post("/", response_model=PredictionOut, status_code=201)
async def create_or_update_prediction(
    data: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = await match_crud.get_by_id(db, data.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    await ensure_predictable(db, match, _TOURNAMENT_TZ)
    fg_player_id, fg_player_name = await _validate_first_goal_player(
        db, match, data.first_goal_player_id
    )

    prediction = await prediction_crud.upsert(
        db,
        user_id=current_user.id,
        match_id=data.match_id,
        predicted_home=data.predicted_home,
        predicted_away=data.predicted_away,
        first_goal_player_id=fg_player_id,
        first_goal_player=fg_player_name,
    )
    await annotate_predictable(db, [prediction.match], _TOURNAMENT_TZ)
    return prediction


@router.delete("/{prediction_id}", status_code=204)
async def delete_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prediction = await prediction_crud.get_by_id_and_user(db, prediction_id, current_user.id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Predicción no encontrada.")
    # Misma ventana que crear/editar: cerrado el plazo de la jornada (o empezado el
    # partido) el pronóstico queda sellado, tampoco se borra.
    await ensure_predictable(db, await match_crud.get_by_id(db, prediction.match_id), _TOURNAMENT_TZ)
    await prediction_crud.delete(db, prediction)


# ── Backfill admin ────────────────────────────────────────────────────────────

async def _resolve_backfill_match(
    db: AsyncSession, item: PredictionBackfillItem
) -> tuple[Match, int, int]:
    """Partido de un item del backfill, por `match_id` o por el par de equipos, con el
    marcador orientado al local/visitante del fixture (por si el par viene invertido)."""
    if item.match_id is not None:
        match = await match_crud.get_by_id(db, item.match_id)
        if not match:
            raise HTTPException(status_code=404, detail=f"Partido {item.match_id} no encontrado.")
        return match, item.predicted_home, item.predicted_away

    matches = await match_crud.get_by_teams(db, item.home_team, item.away_team)
    if not matches:
        raise HTTPException(
            status_code=404, detail=f"No hay partido entre '{item.home_team}' y '{item.away_team}'."
        )
    if len(matches) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Hay {len(matches)} partidos entre '{item.home_team}' y '{item.away_team}' "
                   "(ida y vuelta): usa match_id.",
        )
    match = matches[0]
    if item.home_team == match.home_team:
        return match, item.predicted_home, item.predicted_away
    return match, item.predicted_away, item.predicted_home


async def _resolve_first_goal(
    db: AsyncSession, match: Match, player_id: int | None, player_name: str | None
) -> tuple[int | None, str | None]:
    """Primer goleador del backfill: por id (misma validación que el POST del usuario)
    o por nombre, buscado en las plantillas del partido. Sin coincidencia o ambiguo → 400."""
    if player_id is not None:
        return await _validate_first_goal_player(db, match, player_id)
    if player_name is None:
        return None, None
    players = await player_crud.get_for_teams(
        db, [match.home_team, match.away_team], name_query=player_name
    )
    if not players:
        raise HTTPException(
            status_code=400,
            detail=f"No hay jugador '{player_name}' en {match.home_team} ni {match.away_team}.",
        )
    if len(players) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"'{player_name}' es ambiguo ({len(players)} jugadores): precisa el nombre "
                   "o usa first_goal_player_id.",
        )
    return players[0].api_player_id, players[0].name


@router.post(
    "/admin/backfill",
    response_model=list[PredictionOut],
    status_code=201,
    summary="Admin: cargar pronósticos de un participante (backfill)",
)
async def backfill_predictions(
    data: PredictionBackfillRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Carga (o corrige) los pronósticos de UN participante hechos fuera de la app
    (papel, WhatsApp). A diferencia del POST del usuario NO valida el plazo de la
    jornada ni el estado del partido (por eso es admin): sirve para partidos ya
    jugados. Upsert por (usuario, partido): reenviar corrige, no duplica. Atómico: un
    item inválido (404/400) no carga ninguno. Si algún partido ya FINALIZÓ, corre el
    mismo pipeline del scheduler (primer gol → puntos) para puntuarlo al instante, sin
    esperar al timer de respaldo."""
    user = await user_crud.get_by_team_name(db, data.team_name)
    if not user:
        raise HTTPException(status_code=404, detail=f"Participante '{data.team_name}' no encontrado.")

    saved: list[Prediction] = []
    any_finished = False
    for item in data.predictions:
        match, home, away = await _resolve_backfill_match(db, item)
        any_finished = any_finished or match.status == MatchStatus.FINISHED
        fg_player_id, fg_player_name = await _resolve_first_goal(
            db, match, item.first_goal_player_id, item.first_goal_player
        )
        saved.append(await prediction_crud.upsert(
            db,
            user_id=user.id,
            match_id=match.id,
            predicted_home=home,
            predicted_away=away,
            first_goal_player_id=fg_player_id,
            first_goal_player=fg_player_name,
        ))

    if any_finished:
        # Los jobs abren su propia sesión y solo ven lo confirmado: commit antes. Mismo
        # orden que el scheduler (primer gol → puntos); ambos van envueltos en _retry.
        await db.commit()
        await sync_first_goals()
        await calculate_pending_points()
        # Devolver el estado ya puntuado (los jobs escribieron en otra sesión).
        for pred in saved:
            await db.refresh(pred)
            await db.refresh(pred.match)
    await annotate_predictable(db, [p.match for p in saved], _TOURNAMENT_TZ)
    return saved
