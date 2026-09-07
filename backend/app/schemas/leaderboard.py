from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    team_name: str
    total_points: int
    match_points: int
    top8_points: int
    tournament_points: int   # MVP + máximo goleador
    # Banderas para la vista: qué ya está especificado y qué ya está puntuado (los
    # puntos de Top 8 / torneo solo se muestran cuando ya se calcularon).
    has_top8: bool
    top8_calculated: bool
    tournament_calculated: bool
    predictions_count: int
