from pydantic import BaseModel
from datetime import datetime
from app.models.match import MatchPhase, MatchStatus
from typing import Optional


class MatchOut(BaseModel):
    id: int
    api_fixture_id: int
    home_team: str
    away_team: str
    home_team_logo: Optional[str]
    away_team_logo: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    penalty_home: Optional[int]
    penalty_away: Optional[int]
    elapsed: Optional[int]
    first_goal_team: Optional[str]
    first_goal_player: Optional[str]
    phase: MatchPhase
    status: MatchStatus
    match_date: datetime
    # ¿Se puede pronosticar ahora? (plazo de la jornada + interruptor de prórroga).
    # Lo calcula el backend (services/prediction_window); el frontend solo lo lee.
    predictable: bool = False

    model_config = {"from_attributes": True}
