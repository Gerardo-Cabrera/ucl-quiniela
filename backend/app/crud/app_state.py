from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_state import AppState

_SINGLETON_ID = 1


class AppStateCRUD:
    """Acceso a la fila única de estado global.

    Leer NUNCA escribe: los GET van en una sesión de solo lectura (autocommit) y varias
    vistas consultan este estado en cada refresco. Si la fila falta (la migración 0006 la
    siembra en producción; en los tests se parte de un `create_all` sin ella), las
    lecturas devuelven los valores por defecto y es la primera ESCRITURA la que la crea."""

    async def _find(self, db: AsyncSession) -> AppState | None:
        return await db.get(AppState, _SINGLETON_ID)

    async def get(self, db: AsyncSession) -> AppState:
        """La fila, creándola si falta. Solo para escribir (lo usan los `set_*`)."""
        state = await self._find(db)
        if state is None:
            state = AppState(id=_SINGLETON_ID, prediction_override=False)
            db.add(state)
            await db.flush()
        return state

    async def get_prediction_override(self, db: AsyncSession) -> bool:
        state = await self._find(db)
        return bool(state and state.prediction_override)

    async def set_prediction_override(self, db: AsyncSession, enabled: bool) -> AppState:
        state = await self.get(db)
        state.prediction_override = enabled
        await db.flush()
        return state

    async def get_top8_actual(self, db: AsyncSession) -> list[str]:
        """Top 8 real ordenado 1.º-8.º (vacío hasta que se calcula)."""
        state = await self._find(db)
        return (state.top8_actual if state else None) or []

    async def set_top8_actual(self, db: AsyncSession, teams: list[str]) -> None:
        state = await self.get(db)
        state.top8_actual = list(teams)
        await db.flush()

    async def get_squads_synced_at(self, db: AsyncSession) -> datetime | None:
        state = await self._find(db)
        return state.squads_synced_at if state else None

    async def set_squads_synced_at(self, db: AsyncSession, when: datetime) -> None:
        state = await self.get(db)
        state.squads_synced_at = when
        await db.flush()


app_state_crud = AppStateCRUD()
