from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    team_name: str
    total_points: int
    match_points: int
    top8_points: int
    tournament_points: int   # MVP + máximo goleador
    predictions_count: int
