from datetime import date, datetime, tzinfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.match import Match, MatchPhase, MatchStatus
from app.core.time import as_utc, tz_day


class MatchCRUD:
    async def get_all(
        self,
        db: AsyncSession,
        *,
        phase: MatchPhase | None = None,
        status: MatchStatus | None = None,
    ) -> list[Match]:
        query = select(Match).order_by(Match.match_date)
        if phase:
            query = query.where(Match.phase == phase)
        if status:
            query = query.where(Match.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, match_id: int) -> Match | None:
        result = await db.execute(select(Match).where(Match.id == match_id))
        return result.scalar_one_or_none()

    async def day_first_kickoffs(self, db: AsyncSession, tz: tzinfo) -> dict[date, datetime]:
        """Hora (UTC-aware) del PRIMER partido de cada jornada (día en la zona del
        torneo). Una sola consulta ligera (solo la columna fecha) + agrupación en
        Python: sirve para el plazo de pronósticos sin N+1. Considera TODOS los
        partidos del día, no solo los filtrados, para no perder el kickoff real."""
        result = await db.execute(select(Match.match_date))
        firsts: dict[date, datetime] = {}
        for (match_date,) in result.all():
            md = as_utc(match_date)
            day = tz_day(match_date, tz)
            if day not in firsts or md < firsts[day]:
                firsts[day] = md
        return firsts


match_crud = MatchCRUD()
