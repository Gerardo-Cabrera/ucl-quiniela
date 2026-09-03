from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.team import Team
from app.crud._upsert import upsert_by_key


class TeamCRUD:
    async def get_all_names(self, db: AsyncSession) -> list[str]:
        """Nombres de los clubes ordenados alfabéticamente (para el Top 8)."""
        result = await db.execute(select(Team.name).order_by(Team.name))
        return [row[0] for row in result.all()]

    async def get_names_by_api_ids(self, db: AsyncSession, api_ids: list[int]) -> dict[int, str]:
        """`api_team_id` → nombre: traduce ids de la API (p. ej. de `/standings`) a los
        nombres con los que se guardan los picks del Top 8."""
        result = await db.execute(
            select(Team.api_team_id, Team.name).where(Team.api_team_id.in_(api_ids))
        )
        return dict(result.all())

    async def upsert_many(self, db: AsyncSession, teams: list[dict]) -> int:
        """Inserta o actualiza clubes por `api_team_id`. Idempotente."""
        return await upsert_by_key(db, Team, teams, "api_team_id")

    async def delete_except(self, db: AsyncSession, keep_api_ids: set[int]) -> int:
        """Elimina los clubes cuyo `api_team_id` NO esté en `keep_api_ids`. Reconcilia
        la tabla al set elegible tras un sync con éxito (quita, p. ej., clubes de la
        fase previa que dejaron corridas antiguas). El caller garantiza que el set no
        esté vacío para no borrar todo ante una respuesta anómala de la API."""
        result = await db.execute(delete(Team).where(Team.api_team_id.not_in(keep_api_ids)))
        return result.rowcount


team_crud = TeamCRUD()
