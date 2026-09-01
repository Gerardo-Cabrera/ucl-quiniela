from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.tournament import (
    TournamentPredictionCreate, TournamentPredictionOut, TournamentCalculateRequest,
)
from app.core.deps import get_current_user, get_admin_user
from app.crud import tournament_crud, player_crud, match_crud

router = APIRouter(prefix="/tournament", tags=["Tournament"])


async def _resolve_player(db: AsyncSession, player_id: int | None) -> tuple[int | None, str | None]:
    """Valida el jugador (debe existir en la plantilla sincronizada) y devuelve
    (api_player_id, nombre) para persistir, o (None, None) si no se pronostica."""
    if player_id is None:
        return None, None
    player = await player_crud.get_by_api_id(db, player_id)
    if player is None:
        raise HTTPException(status_code=400, detail=f"El jugador {player_id} no existe.")
    return player.api_player_id, player.name


@router.get("/me", response_model=Optional[TournamentPredictionOut])
async def get_my_tournament(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await tournament_crud.get_by_user(db, current_user.id)


@router.get("/user/{user_id}", response_model=Optional[TournamentPredictionOut])
async def get_user_tournament(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """MVP/máximo goleador de otro participante, revelado una vez que **arranca la
    fase eliminatoria** (mismo cierre que la edición). Antes, nada (null)."""
    if not await match_crud.knockout_started(db):
        return None
    return await tournament_crud.get_by_user(db, user_id)


@router.post("/", response_model=TournamentPredictionOut, status_code=201)
async def save_tournament(
    data: TournamentPredictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fija/actualiza mi MVP y máximo goleador. Editable hasta que arranca el primer
    partido de eliminatoria; luego queda cerrado."""
    if await match_crud.knockout_started(db):
        raise HTTPException(
            status_code=400,
            detail="El MVP y el máximo goleador solo se pueden definir antes de la fase eliminatoria.",
        )
    mvp_id, mvp_name = await _resolve_player(db, data.mvp_player_id)
    scorer_id, scorer_name = await _resolve_player(db, data.top_scorer_player_id)
    return await tournament_crud.upsert(
        db, current_user.id,
        mvp_player_id=mvp_id, mvp_player=mvp_name,
        top_scorer_player_id=scorer_id, top_scorer_player=scorer_name,
    )


@router.post("/calculate", summary="Admin: calcular MVP y máximo goleador")
async def calculate_tournament(
    data: TournamentCalculateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Recibe el MVP y el máximo goleador reales (ids de jugador) y puntúa a todos.
    Idempotente: puede reejecutarse para corregir."""
    for pid in (data.mvp_player_id, data.top_scorer_player_id):
        if await player_crud.get_by_api_id(db, pid) is None:
            raise HTTPException(status_code=400, detail=f"El jugador {pid} no existe.")
    summary = await tournament_crud.calculate_all(db, data.mvp_player_id, data.top_scorer_player_id)
    return {"message": "MVP y máximo goleador calculados.", **summary}
