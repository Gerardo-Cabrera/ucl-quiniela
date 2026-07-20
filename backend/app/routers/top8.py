from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas import Top8PicksCreate, Top8PickOut, Top8CalculateRequest
from app.core.deps import get_current_user, get_admin_user
from app.crud import top8_crud, team_crud, match_crud
from app.config import settings

router = APIRouter(prefix="/top8", tags=["Top 8"])


async def _validate_teams(db: AsyncSession, teams: list[str]) -> None:
    """Valida que los equipos existan en la UCL (clubes sincronizados desde la API)
    y no haya repetidos."""
    valid = {n.lower() for n in await team_crud.get_all_names(db)}
    unknown = [t for t in teams if t.lower() not in valid]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Equipos no válidos de la UCL: {', '.join(unknown)}.",
        )
    lowered = [t.lower() for t in teams]
    if len(set(lowered)) != len(lowered):
        raise HTTPException(status_code=400, detail="No puedes repetir equipos.")


@router.get("/me", response_model=list[Top8PickOut])
async def get_my_top8(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await top8_crud.get_by_user(db, current_user.id)


@router.post("/", response_model=list[Top8PickOut], status_code=201)
async def save_top8(
    data: Top8PicksCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = settings.TOP8_PICK_COUNT
    if len(data.picks) != n:
        raise HTTPException(status_code=400, detail=f"Debes seleccionar exactamente {n} equipos.")

    positions = [p.position for p in data.picks]
    if sorted(positions) != list(range(1, n + 1)):
        raise HTTPException(status_code=400, detail="Las posiciones deben ser del 1 al 8 sin repetir.")

    await _validate_teams(db, [p.team_name for p in data.picks])

    # El Top 8 se fija antes de que arranque la temporada (predice la fase de liga).
    if await match_crud.season_started(db):
        raise HTTPException(
            status_code=400,
            detail="El Top 8 solo puede definirse antes del primer partido de la temporada.",
        )

    if await top8_crud.has_calculated_picks(db, current_user.id):
        raise HTTPException(
            status_code=400,
            detail="No puedes modificar tu Top 8 una vez que ya fue calculado.",
        )

    picks_data = [{"position": p.position, "team_name": p.team_name} for p in data.picks]
    return await top8_crud.replace_picks(db, current_user.id, picks_data)


@router.get("/all", response_model=dict)
async def get_all_top8(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna todos los Top 8 de todos los participantes (para comparar)."""
    return await top8_crud.get_all_with_users(db)


@router.post("/calculate", summary="Admin: Calcular puntos Top 8")
async def calculate_top8(
    data: Top8CalculateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """
    Recibe el Top 8 real (ordenado 1-8) y calcula los puntos de todos
    los participantes. Idempotente: puede reejecutarse para corregir.
    """
    await _validate_teams(db, data.actual_top8)
    summary = await top8_crud.calculate_all(db, data.actual_top8)
    return {"message": "Puntos Top 8 calculados.", **summary}
