from datetime import datetime
from pydantic import BaseModel


class UserCount(BaseModel):
    team_name: str
    count: int


class FirstGoalMatch(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    match_date: datetime
    scorer: str | None          # goleador real del primer gol
    hitters: list[str]          # equipos que lo acertaron (solo se listan si ≥1)


class ScoreMatch(BaseModel):
    """Partido con acierto de marcador exacto, victoria o empate: marcador real y
    quiénes acertaron (solo se listan partidos con ≥1 acierto)."""
    match_id: int
    home_team: str
    away_team: str
    match_date: datetime
    score: str                  # marcador real, "2-1"
    hitters: list[str]


class ScoreCount(BaseModel):
    score: str                  # "2-1"
    count: int


class StatsSummary(BaseModel):
    """Por tipo de acierto: ranking por usuario (desc) y partidos CON acierto (más
    reciente primero). Un marcador exacto cuenta también como victoria o empate."""
    first_goal_matches: list[FirstGoalMatch]
    first_goal_ranking: list[UserCount]
    top_scores: list[ScoreCount]               # marcador(es) real(es) más repetido(s)
    exact_matches: list[ScoreMatch]
    exact_ranking: list[UserCount]
    win_matches: list[ScoreMatch]              # ganador acertado
    win_ranking: list[UserCount]
    draw_matches: list[ScoreMatch]             # empate acertado
    draw_ranking: list[UserCount]
