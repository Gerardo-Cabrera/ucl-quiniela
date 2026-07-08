from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.player import Player
from app.crud._upsert import upsert_by_key


class PlayerCRUD:
    async def get_for_teams(self, db: AsyncSession, team_names: list[str]) -> list[Player]:
        """Jugadores de los equipos dados (para el selector de primer goleador),
        ordenados por equipo y nombre."""
        if not team_names:
            return []
        result = await db.execute(
            select(Player)
            .where(Player.team_name.in_(team_names))
            .order_by(Player.team_name, Player.name)
        )
        return list(result.scalars().all())

    async def get_by_api_id(self, db: AsyncSession, api_player_id: int) -> Player | None:
        result = await db.execute(
            select(Player).where(Player.api_player_id == api_player_id)
        )
        return result.scalar_one_or_none()

    async def upsert_many(self, db: AsyncSession, players: list[dict]) -> int:
        """Inserta o actualiza jugadores por `api_player_id`. Idempotente."""
        return await upsert_by_key(db, Player, players, "api_player_id")


player_crud = PlayerCRUD()
