from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.crud import team_crud

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/teams")
async def get_teams(db: AsyncSession = Depends(get_db)):
    """Clubes UCL (sincronizados desde API-Football) para el selector del Top 8.
    Público, sin auth. Vacío hasta que la API publique los equipos de la temporada."""
    return {"ucl_teams": await team_crud.get_all_names(db)}
