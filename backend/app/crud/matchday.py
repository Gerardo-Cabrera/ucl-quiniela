from collections import defaultdict
from datetime import date, tzinfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.core.time import tz_day
from app.schemas.matchday import (
    MatchdayEntry, MatchdayUserPoints, MatchdaysSummary, MvpRankEntry, PointsGroup, RoundEntry,
)


def _rank(points: dict[int, list]) -> tuple[list[MatchdayUserPoints], int, list[str]]:
    """Entradas ordenadas por puntos (desc, desempate alfabético), puntos del MVP y
    MVP(s): quienes tienen el máximo, si es > 0."""
    entries = sorted(
        (MatchdayUserPoints(user_id=uid, team_name=tn, points=pts) for uid, (tn, pts) in points.items()),
        key=lambda e: (-e.points, e.team_name),
    )
    top = entries[0].points if entries else 0
    mvps = [e.team_name for e in entries if e.points == top] if top > 0 else []
    return entries, top, mvps


def _mvp_ranking(groups: list[PointsGroup]) -> list[MvpRankEntry]:
    """Veces que cada equipo fue MVP en los grupos COMPLETOS (uno en curso aún puede
    cambiar de MVP): desc por veces, desempate alfabético."""
    counts: dict[str, int] = defaultdict(int)
    for g in groups:
        if g.complete:
            for tn in g.mvps:
                counts[tn] += 1
    return sorted(
        (MvpRankEntry(team_name=tn, count=c) for tn, c in counts.items()),
        key=lambda r: (-r.count, r.team_name),
    )


class MatchdayCRUD:
    async def get_summary(self, db: AsyncSession, tz: tzinfo) -> MatchdaysSummary:
        """Puntos por participante y MVP(s) de cada día de partidos (en la zona del
        torneo) y de cada jornada completa (ronda de la API: 'League Stage - N',
        martes a jueves; en eliminatorias, la fase con sus dos partidos). Solo cuenta
        predicciones ya calculadas de cuentas activas. `complete`: todos los partidos
        del grupo terminaron (o se pospusieron) y están puntuados, condición para
        compartir su MVP y para contar en el histórico y el ranking de MVPs. Tres
        consultas ligeras + agregación en Python (cross-DB)."""
        matches = (await db.execute(
            select(Match.id, Match.match_date, Match.phase, Match.round_number, Match.status)
        )).all()
        pending = set((await db.execute(
            select(Prediction.match_id).where(Prediction.is_calculated.is_(False)).distinct()
        )).scalars())
        scored = (await db.execute(
            select(User.id, User.team_name, Prediction.match_id, Prediction.points_earned)
            .select_from(Prediction).join(User)
            .where(Prediction.is_calculated.is_(True), User.is_active.is_(True))
        )).all()

        day_of = {m.id: tz_day(m.match_date, tz) for m in matches}
        round_of = {m.id: (m.phase, m.round_number) for m in matches}
        unfinished = [
            m.id for m in matches
            if m.status not in (MatchStatus.FINISHED, MatchStatus.POSTPONED) or m.id in pending
        ]
        incomplete_days = {day_of[mid] for mid in unfinished}
        incomplete_rounds = {round_of[mid] for mid in unfinished}
        round_days: dict[tuple, set[date]] = defaultdict(set)
        for mid, day in day_of.items():
            round_days[round_of[mid]].add(day)

        # grupo -> user_id -> [team_name, puntos acumulados]
        by_day: dict[date, dict[int, list]] = defaultdict(dict)
        by_round: dict[tuple, dict[int, list]] = defaultdict(dict)
        for uid, team, mid, pts in scored:
            for groups, key in ((by_day, day_of[mid]), (by_round, round_of[mid])):
                acc = groups[key].setdefault(uid, [team, 0])
                acc[1] += pts

        days: list[MatchdayEntry] = []
        for day in sorted(by_day):
            entries, top, mvps = _rank(by_day[day])
            days.append(MatchdayEntry(
                date=day, entries=entries, mvp_points=top, mvps=mvps,
                complete=day not in incomplete_days,
            ))

        rounds: list[RoundEntry] = []
        for key in sorted(by_round, key=lambda k: min(round_days[k])):
            entries, top, mvps = _rank(by_round[key])
            rounds.append(RoundEntry(
                phase=key[0], round_number=key[1],
                start=min(round_days[key]), end=max(round_days[key]),
                entries=entries, mvp_points=top, mvps=mvps,
                complete=key not in incomplete_rounds,
            ))

        return MatchdaysSummary(
            days=days, rounds=rounds,
            day_mvp_ranking=_mvp_ranking(days), round_mvp_ranking=_mvp_ranking(rounds),
        )


matchday_crud = MatchdayCRUD()
