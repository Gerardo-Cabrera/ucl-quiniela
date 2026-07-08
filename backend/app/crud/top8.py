from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.top8_pick import Top8Pick
from app.models.user import User
from app.services.scoring import calculate_top8_points


class Top8CRUD:
    async def get_by_user(self, db: AsyncSession, user_id: int) -> list[Top8Pick]:
        result = await db.execute(
            select(Top8Pick)
            .where(Top8Pick.user_id == user_id)
            .order_by(Top8Pick.position)
        )
        return list(result.scalars().all())

    async def has_calculated_picks(self, db: AsyncSession, user_id: int) -> bool:
        result = await db.execute(
            select(Top8Pick.id)
            .where(
                Top8Pick.user_id == user_id,
                Top8Pick.is_calculated == True,  # noqa: E712
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def replace_picks(
        self,
        db: AsyncSession,
        user_id: int,
        picks: list[dict],
    ) -> list[Top8Pick]:
        await db.execute(delete(Top8Pick).where(Top8Pick.user_id == user_id))
        new_picks = [
            Top8Pick(
                user_id=user_id,
                position=pick["position"],
                team_name=pick["team_name"],
            )
            for pick in picks
        ]
        db.add_all(new_picks)
        await db.flush()
        result = await db.execute(
            select(Top8Pick)
            .where(Top8Pick.user_id == user_id)
            .order_by(Top8Pick.position)
        )
        return list(result.scalars().all())

    async def calculate_all(self, db: AsyncSession, actual_top8: list[str]) -> dict:
        """
        Calcula y persiste los puntos de los picks Top 8 de TODOS los usuarios
        contra el Top 8 real (ordenado 1-8). Idempotente: recalcula si se reejecuta.
        """
        result = await db.execute(select(Top8Pick))
        picks = list(result.scalars().all())

        scored = calculate_top8_points(
            [{"position": p.position, "team_name": p.team_name} for p in picks],
            actual_top8,
        )
        for pick, score in zip(picks, scored):
            pick.points_earned = score["points_earned"]
            pick.is_calculated = True

        await db.flush()
        return {
            "picks_calculated": len(picks),
            "users_affected": len({p.user_id for p in picks}),
        }

    async def get_all_with_users(self, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Top8Pick, User.team_name.label("user_team"))
            .join(User, Top8Pick.user_id == User.id)
            .order_by(User.team_name, Top8Pick.position)
        )
        rows = result.all()
        grouped: dict = {}
        for pick, user_team in rows:
            if user_team not in grouped:
                grouped[user_team] = []
            grouped[user_team].append({
                "position": pick.position,
                "team": pick.team_name,
                "points": pick.points_earned,
            })
        return grouped


top8_crud = Top8CRUD()
