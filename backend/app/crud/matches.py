from datetime import date, datetime, timezone, tzinfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select
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

    async def get_by_teams(self, db: AsyncSession, home_team: str, away_team: str) -> list[Match]:
        """Partidos entre esos dos equipos en CUALQUIER orden (backfill por nombres, sin
        conocer el id). En la fase de liga el par es único; en eliminatorias hay ida y
        vuelta (dos partidos): el caller pide entonces `match_id`."""
        result = await db.execute(
            select(Match)
            .where(or_(
                and_(Match.home_team == home_team, Match.away_team == away_team),
                and_(Match.home_team == away_team, Match.away_team == home_team),
            ))
            .order_by(Match.match_date)
        )
        return list(result.scalars().all())

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

    async def season_started(self, db: AsyncSession) -> bool:
        """True si el primer partido de la temporada ya arrancó (min kickoff ≤ ahora).
        Cierre del Top 8: se predicen las posiciones de la fase de liga, así que se
        fija antes de que empiece. Una sola consulta agregada."""
        first = (await db.execute(select(func.min(Match.match_date)))).scalar()
        return first is not None and as_utc(first) <= datetime.now(timezone.utc)

    async def round_of_16_started(self, db: AsyncSession) -> bool:
        """True si arrancó el primer partido de OCTAVOS de final (o de una fase
        posterior). Cierre del MVP y el máximo goleador: editables durante la fase de
        liga y los play-offs, se fijan al empezar los octavos. Antes de eso (o sin
        esos fixtures) es editable. Una sola consulta agregada."""
        first = (await db.execute(
            select(func.min(Match.match_date)).where(
                Match.phase.not_in([MatchPhase.LEAGUE, MatchPhase.KNOCKOUT_PLAYOFFS])
            )
        )).scalar()
        return first is not None and as_utc(first) <= datetime.now(timezone.utc)


match_crud = MatchCRUD()
