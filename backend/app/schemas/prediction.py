from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from app.schemas.match import MatchOut


def _reject_scorer_on_goalless(predicted_home: int, predicted_away: int, has_scorer: bool) -> None:
    """Un 0-0 no tiene primer gol: un goleador ahí es incoherente. La UI oculta el
    selector y limpia la elección; esto cubre clientes o llamadas directas. Regla
    única para el pronóstico del usuario y el backfill admin."""
    if has_scorer and predicted_home + predicted_away == 0:
        raise ValueError("Un marcador 0-0 no admite primer goleador.")


def _blank_to_none(v: Optional[str]) -> Optional[str]:
    v = (v or "").strip()
    return v or None


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    # Pronóstico del primer goleador: id de API-Football del jugador (debe jugar
    # en uno de los dos equipos del partido). Opcional.
    first_goal_player_id: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def _check(self) -> "PredictionCreate":
        _reject_scorer_on_goalless(self.predicted_home, self.predicted_away, self.first_goal_player_id is not None)
        return self


class PredictionBackfillItem(BaseModel):
    """Un pronóstico del backfill admin. El partido se identifica por `match_id` **o**
    por el par de equipos (`home_team`/`away_team`, en cualquier orden: el marcador se
    orienta al local/visitante del fixture). El primer goleador, por id **o** por
    nombre (`first_goal_player`, se busca en las plantillas del partido)."""
    match_id: Optional[int] = None
    home_team: Optional[str] = Field(default=None, max_length=100)
    away_team: Optional[str] = Field(default=None, max_length=100)
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    first_goal_player_id: Optional[int] = None
    first_goal_player: Optional[str] = Field(default=None, max_length=100)

    _strip = field_validator("home_team", "away_team", "first_goal_player")(_blank_to_none)

    @model_validator(mode="after")
    def _check(self) -> "PredictionBackfillItem":
        if self.match_id is None and not (self.home_team and self.away_team):
            raise ValueError("Indica match_id, o home_team y away_team.")
        has_scorer = self.first_goal_player_id is not None or self.first_goal_player is not None
        _reject_scorer_on_goalless(self.predicted_home, self.predicted_away, has_scorer)
        return self


class PredictionBackfillRequest(BaseModel):
    """Carga admin de los pronósticos de UN participante (por `team_name`) hechos fuera
    de la app (papel, WhatsApp): sin validar el plazo de la jornada."""
    team_name: str = Field(min_length=1, max_length=100)
    predictions: list[PredictionBackfillItem] = Field(min_length=1)


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
