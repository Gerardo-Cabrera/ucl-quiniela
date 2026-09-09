from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tournament_prediction import TournamentPrediction
from app.models.match import Match, MatchStatus
from app.models.player import Player
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

    async def get_leaders(self, db: AsyncSession, limit: int = 10) -> dict[str, list[dict]]:
        """Goleadores y asistidores de la quiniela (fase de liga en adelante), agregados
        de los goles guardados por partido finalizado (`Match.goal_events`). Sin cuota
        de API (los eventos ya se descargan para el primer gol) y sin almacenar
        rankings. Empates: por nombre."""
        rows = (await db.execute(
            select(Match.goal_events).where(
                Match.status == MatchStatus.FINISHED, Match.goal_events.is_not(None)
            )
        )).scalars().all()
        players: dict[int, dict] = {}

        def bump(pid: int | None, name: str | None, team: str | None, key: str) -> None:
            if pid is None:
                return
            row = players.setdefault(pid, {"player_id": pid, "name": name, "team": team, "goals": 0, "assists": 0})
            row[key] += 1

        for goals in rows:
            for g in goals:
                bump(g.get("player_id"), g.get("player"), g.get("team"), "goals")
                bump(g.get("assist_id"), g.get("assist"), g.get("team"), "assists")

        photos: dict[int, str | None] = {}
        if players:
            photos = dict((await db.execute(
                select(Player.api_player_id, Player.photo).where(Player.api_player_id.in_(list(players)))
            )).all())
        for row in players.values():
            row["photo"] = photos.get(row["player_id"])

        def top(key: str) -> list[dict]:
            ranked = sorted((r for r in players.values() if r[key] > 0), key=lambda r: (-r[key], r["name"] or ""))
            return ranked[:limit]

        return {"top_scorers": top("goals"), "top_assists": top("assists")}


tournament_crud = TournamentCRUD()
