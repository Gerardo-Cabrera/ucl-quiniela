from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tournament_prediction import TournamentPrediction
from app.config import settings


class TournamentCRUD:
    async def get_by_user(self, db: AsyncSession, user_id: int) -> TournamentPrediction | None:
        result = await db.execute(
            select(TournamentPrediction).where(TournamentPrediction.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self, db: AsyncSession, user_id: int, *,
        mvp_player_id: int | None, mvp_player: str | None,
        top_scorer_player_id: int | None, top_scorer_player: str | None,
    ) -> TournamentPrediction:
        """Crea o actualiza el pronóstico del usuario (una fila por usuario). Al editar
        se resetean puntos y el flag de calculado."""
        obj = await self.get_by_user(db, user_id)
        if obj is None:
            obj = TournamentPrediction(user_id=user_id)
            db.add(obj)
        obj.mvp_player_id = mvp_player_id
        obj.mvp_player = mvp_player
        obj.top_scorer_player_id = top_scorer_player_id
        obj.top_scorer_player = top_scorer_player
        obj.mvp_points = 0
        obj.top_scorer_points = 0
        obj.is_calculated = False
        await db.flush()
        return obj

    async def calculate_all(
        self, db: AsyncSession, mvp_player_id: int, top_scorer_player_id: int
    ) -> dict:
        """Puntúa a todos: TOURNAMENT_PICK_POINTS por acierto de MVP y de goleador (por
        id), por separado. Idempotente (reejecutable para corregir)."""
        pts = settings.TOURNAMENT_PICK_POINTS
        rows = list((await db.execute(select(TournamentPrediction))).scalars().all())
        for r in rows:
            r.mvp_points = pts if r.mvp_player_id == mvp_player_id else 0
            r.top_scorer_points = pts if r.top_scorer_player_id == top_scorer_player_id else 0
            r.is_calculated = True
        await db.flush()
        return {"users_affected": len(rows)}


tournament_crud = TournamentCRUD()
