from datetime import date
from pydantic import BaseModel
from app.models.match import MatchPhase


class MatchdayUserPoints(BaseModel):
    user_id: int
    team_name: str
    points: int


class PointsGroup(BaseModel):
    """Puntos de un grupo de partidos (un día o una jornada completa)."""
    # Participantes con predicción ya calculada en el grupo, ordenados por puntos (desc).
    entries: list[MatchdayUserPoints]
    mvp_points: int          # puntos del MVP (0 si nadie puntuó)
    mvps: list[str]          # equipo(s) con más puntos (>0); vacío si mvp_points == 0
    complete: bool           # todos los partidos terminaron y están puntuados: se puede compartir


class MatchdayEntry(PointsGroup):
    date: date


class RoundEntry(PointsGroup):
    """Jornada completa: ronda de la API ('League Stage - N' = martes a jueves; en
    eliminatorias, la fase con sus dos partidos)."""
    phase: MatchPhase
    round_number: int | None   # jornada de la fase de liga; None en eliminatorias
    start: date                # primer y último día con partidos de la ronda
    end: date


class MvpRankEntry(BaseModel):
    team_name: str
    count: int               # veces que fue MVP de un día


class MatchdaysSummary(BaseModel):
    days: list[MatchdayEntry]        # cronológico ascendente
    rounds: list[RoundEntry]         # cronológico ascendente (por su primer día)
    mvp_ranking: list[MvpRankEntry]  # MVPs del día: desc por count, desempate alfabético
