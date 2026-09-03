from typing import Optional
from pydantic import BaseModel


class TournamentPredictionCreate(BaseModel):
    """Pronóstico de MVP y máximo goleador del torneo (ids de jugador de API-Football;
    opcionales: se puede fijar solo uno)."""
    mvp_player_id: Optional[int] = None
    top_scorer_player_id: Optional[int] = None


class TournamentPredictionOut(BaseModel):
    mvp_player_id: Optional[int]
    mvp_player: Optional[str]
    top_scorer_player_id: Optional[int]
    top_scorer_player: Optional[str]
    mvp_points: int
    top_scorer_points: int
    is_calculated: bool

    model_config = {"from_attributes": True}


class TournamentCalculateRequest(BaseModel):
    """Admin: MVP y máximo goleador reales (ids de jugador) para puntuar a todos."""
    mvp_player_id: int
    top_scorer_player_id: int
