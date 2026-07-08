from pydantic import BaseModel, Field


class Top8PickItem(BaseModel):
    position: int = Field(ge=1, le=8)
    team_name: str = Field(min_length=1, max_length=100)


class Top8PicksCreate(BaseModel):
    picks: list[Top8PickItem]


class Top8CalculateRequest(BaseModel):
    """Top 8 real (ordenado 1-8) para calcular los puntos de todos los participantes."""
    actual_top8: list[str] = Field(min_length=8, max_length=8)


class Top8PickOut(BaseModel):
    id: int
    position: int
    team_name: str
    points_earned: int
    is_calculated: bool

    model_config = {"from_attributes": True}
