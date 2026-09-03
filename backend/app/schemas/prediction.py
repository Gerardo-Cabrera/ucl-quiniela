from pydantic import BaseModel, Field, model_validator
from typing import Optional
from app.schemas.match import MatchOut


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    # Pronóstico del primer goleador: id de API-Football del jugador (debe jugar
    # en uno de los dos equipos del partido). Opcional.
    first_goal_player_id: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def _reject_scorer_on_goalless(self) -> "PredictionCreate":
        # Un 0-0 no tiene primer gol: un goleador ahí es incoherente. La UI oculta el
        # selector y limpia la elección; esto cubre clientes o llamadas directas.
        if self.first_goal_player_id is not None and self.predicted_home + self.predicted_away == 0:
            raise ValueError("Un marcador 0-0 no admite primer goleador.")
        return self


class PredictionOut(BaseModel):
    id: int
    match_id: int
    predicted_home: int
    predicted_away: int
    first_goal_player_id: Optional[int]
    first_goal_player: Optional[str]
    points_earned: int
    first_goal_points: int   # desglose del primer gol (dentro de points_earned)
    is_calculated: bool
    match: MatchOut

    model_config = {"from_attributes": True}


class PredictionOverrideUpdate(BaseModel):
    """Cuerpo del interruptor admin de prórroga de pronósticos."""
    enabled: bool


class PredictionOverrideOut(BaseModel):
    enabled: bool
    lead_minutes: int  # plazo normal: minutos antes del 1er partido del día
