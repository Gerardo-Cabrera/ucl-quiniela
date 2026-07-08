from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.team import Team
from app.crud._upsert import upsert_by_key


class TeamCRUD:
    async def get_all_names(self, db: AsyncSession) -> list[str]:
        """Nombres de los clubes ordenados alfabéticamente (para el Top 8)."""
        result = await db.execute(select(Team.name).order_by(Team.name))
        return [row[0] for row in result.all()]

    async def upsert_many(self, db: AsyncSession, teams: list[dict]) -> int:
        """Inserta o actualiza clubes por `api_team_id`. Idempotente."""
        return await upsert_by_key(db, Team, teams, "api_team_id")


team_crud = TeamCRUD()
