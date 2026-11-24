from pydantic import BaseModel
from typing import Literal, Optional

# Disponibilidad de un jugador para UN partido: lesionado, sancionado (por roja o por
# ciclo de amarillas), duda, o no disponible por otro motivo (fuera de la lista de la
# competición, decisión técnica...). None = sin baja conocida.
Availability = Literal["injured", "suspended", "doubtful", "unavailable"]


class PlayerOut(BaseModel):
    api_player_id: int
    name: str
    team_name: str
    position: Optional[str] = None
    photo: Optional[str] = None   # selector visual del primer goleador

    model_config = {"from_attributes": True}


class PlayerFormOut(PlayerOut):
    """Jugador con sus goles en la quiniela (fase de liga en adelante), para destacar a
    los goleadores al elegir. `team_top_scorer`: es el máximo goleador de su equipo
    (con al menos un gol; si hay empate, lo son todos los empatados)."""
    goals: int = 0
    team_top_scorer: bool = False


class MatchPlayerOut(PlayerFormOut):
    """Jugador de las plantillas de un partido, con lo que conviene saber antes de
    elegirlo como primer goleador: si es baja o duda para ESE partido. La sanción sale
    de las bajas de API-Football y de las tarjetas del partido anterior (reglamento);
    `availability_reason` es el motivo en el vocabulario de la API (en inglés: el
    frontend lo traduce)."""
    availability: Optional[Availability] = None
    availability_reason: Optional[str] = None
