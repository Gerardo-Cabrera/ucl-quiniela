from sqlalchemy.ext.asyncio import AsyncSession
from app.models.app_state import AppState

_SINGLETON_ID = 1


class AppStateCRUD:
    """Acceso a la fila única de estado global. `get` la crea perezosamente si falta
    (la migración 0006 ya la siembra en prod; esto cubre el create_all de los tests)."""

    async def get(self, db: AsyncSession) -> AppState:
        state = await db.get(AppState, _SINGLETON_ID)
        if state is None:
            state = AppState(id=_SINGLETON_ID, prediction_override=False)
            db.add(state)
            await db.flush()
        return state

    async def get_prediction_override(self, db: AsyncSession) -> bool:
        return (await self.get(db)).prediction_override

    async def set_prediction_override(self, db: AsyncSession, enabled: bool) -> AppState:
        state = await self.get(db)
        state.prediction_override = enabled
        await db.flush()
        return state


app_state_crud = AppStateCRUD()
