from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.match import Match
from app.models.user import User
from app.schemas import (
    PredictionCreate, PredictionOut, PredictionOverrideUpdate, PredictionOverrideOut,
)
from app.core.deps import get_current_user, get_admin_user
from app.crud import prediction_crud, match_crud, player_crud, app_state_crud
from app.services.prediction_window import ensure_predictable, annotate_predictable

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

    existing = await prediction_crud.get_by_user_and_match(db, current_user.id, data.match_id)

    if existing:
        prediction = await prediction_crud.update(
            db, existing,
            predicted_home=data.predicted_home,
            predicted_away=data.predicted_away,
            first_goal_player_id=fg_player_id,
            first_goal_player=fg_player_name,
        )
    else:
        prediction = await prediction_crud.create(
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
    if prediction.is_calculated:
        raise HTTPException(status_code=400, detail="No se puede eliminar una predicción ya calculada.")
    await prediction_crud.delete(db, prediction)
