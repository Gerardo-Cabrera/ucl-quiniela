from collections.abc import Iterable
from datetime import date, datetime, timezone, tzinfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import undefer
from app.models.match import Match, MatchPhase, MatchStatus
from app.core.time import as_utc, tz_day


def first_kickoffs_by_day(match_dates: Iterable[datetime], tz: tzinfo) -> dict[date, datetime]:
    """Hora (UTC-aware) del PRIMER partido de cada jornada (día en la zona del torneo)
    a partir de las fechas de los partidos. Regla pura, sin BD: la comparten la consulta
    `MatchCRUD.day_first_kickoffs` y quien ya tiene TODOS los partidos cargados (la
    lista de `/matches`), que así no repite la consulta."""
    firsts: dict[date, datetime] = {}
    for match_date in match_dates:
        md = as_utc(match_date)
        day = tz_day(match_date, tz)
        if day not in firsts or md < firsts[day]:
            firsts[day] = md
    return firsts


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

    @staticmethod
    def by_id_query(match_id: int, *, with_absences: bool = False, for_update: bool = False):
        """Consulta de un partido por id (ver `get_by_id`)."""
        query = select(Match).where(Match.id == match_id)
        if with_absences:
            query = query.options(undefer(Match.absences), undefer(Match.manual_absences))
        if for_update:
            query = query.with_for_update()
        return query

    async def get_by_id(
        self, db: AsyncSession, match_id: int, *, with_absences: bool = False, for_update: bool = False
    ) -> Match | None:
        """`with_absences`: trae también `Match.absences` y `Match.manual_absences`
        (columnas diferidas) en la misma consulta; sin ello, leer esos atributos en una
        sesión async falla.
        `for_update`: bloquea la fila hasta el fin de la transacción (`SELECT ... FOR
        UPDATE`). Para leer-modificar-escribir un JSON del partido sin que dos peticiones
        simultáneas partan de la misma lectura y la segunda pise a la primera."""
        result = await db.execute(
            self.by_id_query(match_id, with_absences=with_absences, for_update=for_update)
        )
        return result.scalar_one_or_none()

    async def set_manual_absence(
        self, db: AsyncSession, match: Match, player_id: int, entry: dict | None
    ) -> None:
        """Fija (o, con `entry=None`, quita) la corrección manual de un jugador en un
        partido cargado con `with_absences=True` y `for_update=True` (la lista entera se
        reescribe: sin el bloqueo, dos correcciones simultáneas de jugadores distintos se
        pisarían). Una por jugador: la nueva sustituye a la anterior. Se asigna una lista
        NUEVA: SQLAlchemy no detecta cambios hechos dentro de un JSON ya cargado."""
        others = [a for a in match.manual_absences or [] if a.get("player_id") != player_id]
        match.manual_absences = others + ([entry] if entry is not None else [])
        await db.flush()

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

    async def get_team_schedules(self, db: AsyncSession, team_names: list[str]):
        """Todos los partidos (del estado que sean) de esos equipos, en orden cronológico,
        con lo que hace falta para las marcas del selector de jugadores: fase, estado y
        los goles y tarjetas guardados. Una sola consulta de pocas filas (un equipo juega
        8 partidos de liga), con las columnas diferidas pedidas de forma explícita."""
        result = await db.execute(
            select(
                Match.id, Match.home_team, Match.away_team, Match.phase, Match.status,
                Match.match_date, Match.goal_events, Match.card_events,
            )
            .where(or_(Match.home_team.in_(team_names), Match.away_team.in_(team_names)))
            .order_by(Match.match_date, Match.id)
        )
        return result.all()

    async def get_goal_events(self, db: AsyncSession) -> list[list[dict]]:
        """Goles guardados de todos los partidos finalizados (uno por partido)."""
        result = await db.execute(
            select(Match.goal_events).where(
                Match.status == MatchStatus.FINISHED, Match.goal_events.is_not(None)
            )
        )
        return list(result.scalars())

    async def day_first_kickoffs(self, db: AsyncSession, tz: tzinfo) -> dict[date, datetime]:
        """Hora (UTC-aware) del PRIMER partido de cada jornada (día en la zona del
        torneo). Una sola consulta ligera (solo la columna fecha) + agrupación en
        Python: sirve para el plazo de pronósticos sin N+1. Considera TODOS los
        partidos del día, no solo los filtrados, para no perder el kickoff real."""
        result = await db.execute(select(Match.match_date))
        return first_kickoffs_by_day(result.scalars(), tz)

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
