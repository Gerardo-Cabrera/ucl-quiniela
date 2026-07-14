from datetime import date, datetime, timezone, tzinfo
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

    async def started_day_match_ids(self, db: AsyncSession, tz: tzinfo) -> set[int]:
        """IDs de los partidos de toda jornada ya INICIADA (su primer partido, en
        `tz`, ya arrancó). Revela el día completo aunque algún partido no haya
        empezado: los pronósticos del día ya cerraron, así que no cambian. Sirve
        para mostrar los pronósticos ajenos sin permitir ver los de días por venir.
        Una sola consulta ligera (id + fecha) y agrupación en Python, como
        `day_first_kickoffs`."""
        now = datetime.now(timezone.utc)
        rows = [
            (mid, tz_day(md, tz), as_utc(md) <= now)
            for mid, md in (await db.execute(select(Match.id, Match.match_date))).all()
        ]
        started_days = {day for _, day, has_started in rows if has_started}
        return {mid for mid, day, _ in rows if day in started_days}


match_crud = MatchCRUD()
