from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.services.scoring import outcome
from app.schemas.stats import FirstGoalMatch, ScoreCount, ScoreMatch, StatsSummary, UserCount

# Tipos de acierto: marcador exacto, primer gol (por jugador), victoria (ganador
# correcto) y empate. Un marcador exacto cuenta también como victoria o empate.
_KINDS = ("exact", "first_goal", "win", "draw")


def _ranking(counts: dict[str, int]) -> list[UserCount]:
    """Ranking desc por nº de aciertos (desempate alfabético); omite a quien no acertó."""
    return sorted(
        (UserCount(team_name=t, count=c) for t, c in counts.items() if c > 0),
        key=lambda u: (-u.count, u.team_name),
    )


class StatsCRUD:
    async def get_summary(self, db: AsyncSession) -> StatsSummary:
        """Aciertos por tipo (ranking + partidos con acierto) y marcador real más
        repetido. Solo cuenta predicciones ya calculadas de cuentas activas en partidos
        finalizados. Dos consultas acotadas + agregación en Python (cross-DB); no hay N+1."""
        matches = (await db.execute(
            select(
                Match.id, Match.home_team, Match.away_team, Match.match_date,
                Match.home_score, Match.away_score,
                Match.first_goal_player_id, Match.first_goal_player,
            )
            .where(Match.status == MatchStatus.FINISHED)
            .order_by(Match.match_date.desc(), Match.id.desc())
        )).all()

        preds = (await db.execute(
            select(
                User.team_name, Prediction.match_id,
                Prediction.predicted_home, Prediction.predicted_away,
                Prediction.first_goal_player_id,
            )
            .select_from(Prediction).join(Match).join(User)
            .where(Prediction.is_calculated.is_(True), User.is_active.is_(True))
        )).all()

        by_id = {m.id: m for m in matches}
        counts: dict[str, dict[str, int]] = {k: defaultdict(int) for k in _KINDS}       # tipo -> equipo -> aciertos
        hitters: dict[str, dict[int, list[str]]] = {k: defaultdict(list) for k in _KINDS}  # tipo -> partido -> equipos

        def hit(kind: str, team: str, match_id: int) -> None:
            counts[kind][team] += 1
            hitters[kind][match_id].append(team)

        for team, match_id, ph, pa, pfg in preds:
            m = by_id.get(match_id)
            if m is None or m.home_score is None or m.away_score is None:
                continue
            if ph == m.home_score and pa == m.away_score:
                hit("exact", team, match_id)
            real = outcome(m.home_score, m.away_score)
            if outcome(ph, pa) == real:
                hit("draw" if real == "draw" else "win", team, match_id)
            # Primer gol por jugador (id), igual que el scoring: ambos deben existir.
            if pfg is not None and m.first_goal_player_id is not None and pfg == m.first_goal_player_id:
                hit("first_goal", team, match_id)

        # Marcador real más repetido (sobre los partidos finalizados; empates → varios).
        score_freq: dict[str, int] = defaultdict(int)
        for m in matches:
            if m.home_score is not None and m.away_score is not None:
                score_freq[f"{m.home_score}-{m.away_score}"] += 1
        top = max(score_freq.values(), default=0)
        top_scores = sorted(
            (ScoreCount(score=s, count=c) for s, c in score_freq.items() if c == top and top > 0),
            key=lambda x: x.score,
        )

        def score_matches(kind: str) -> list[ScoreMatch]:
            """Solo partidos CON acierto de ese tipo, con el marcador real."""
            return [
                ScoreMatch(
                    match_id=m.id, home_team=m.home_team, away_team=m.away_team,
                    match_date=m.match_date, score=f"{m.home_score}-{m.away_score}",
                    hitters=sorted(hitters[kind][m.id]),
                )
                for m in matches if hitters[kind].get(m.id)
            ]

        first_goal_matches = [
            FirstGoalMatch(
                match_id=m.id, home_team=m.home_team, away_team=m.away_team,
                match_date=m.match_date, scorer=m.first_goal_player,
                hitters=sorted(hitters["first_goal"][m.id]),
            )
            for m in matches if hitters["first_goal"].get(m.id)
        ]

        return StatsSummary(
            first_goal_matches=first_goal_matches,
            first_goal_ranking=_ranking(counts["first_goal"]),
            top_scores=top_scores,
            exact_matches=score_matches("exact"),
            exact_ranking=_ranking(counts["exact"]),
            win_matches=score_matches("win"),
            win_ranking=_ranking(counts["win"]),
            draw_matches=score_matches("draw"),
            draw_ranking=_ranking(counts["draw"]),
        )


stats_crud = StatsCRUD()
