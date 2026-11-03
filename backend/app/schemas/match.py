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
    elapsed_extra: Optional[int] = None   # descuento en curso: "90+3"
    # status.short de la API: en vivo, la tarjeta muestra "Descanso" (HT), la pausa de la
    # prórroga (BT), "Penales" (P) o suspendido/interrumpido en vez del minuto.
    api_status: Optional[str] = None
    # Probabilidad de victoria pre-partido (API-Football), solo del próximo partido de
    # cada equipo; null si no se consultó o la API no la entrega.
    prob_home: Optional[int] = None
    prob_draw: Optional[int] = None
    prob_away: Optional[int] = None
    prob_updated_at: Optional[datetime] = None
    first_goal_team: Optional[str]
    first_goal_player: Optional[str]
    # id del goleador real: la tarjeta marca el acierto del primer gol por id (como el scoring).
    first_goal_player_id: Optional[int] = None
    phase: MatchPhase
    status: MatchStatus
    match_date: datetime
    # ¿Se puede pronosticar ahora? (plazo de la jornada + interruptor de prórroga).
    # Lo calcula el backend (services/prediction_window); el frontend solo lo lee.
    predictable: bool = False

    model_config = {"from_attributes": True}
