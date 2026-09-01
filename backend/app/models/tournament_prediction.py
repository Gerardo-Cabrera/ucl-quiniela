from sqlalchemy import Integer, ForeignKey, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class TournamentPrediction(Base):
    """Pronóstico global del torneo por usuario (una fila por usuario): MVP y máximo
    goleador. Se puntúa por id de jugador de API-Football (5 pts por acierto, cada uno).
    Editable hasta que arranca la fase eliminatoria; el admin fija los reales y calcula.
    """
    __tablename__ = "tournament_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)

    # Pronóstico: id de jugador de API-Football (contra lo que se puntúa) + nombre
    # denormalizado (para mostrarlo sin un join a players).
    mvp_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mvp_player: Mapped[str | None] = mapped_column(String(100), nullable=True)
    top_scorer_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_scorer_player: Mapped[str | None] = mapped_column(String(100), nullable=True)

    mvp_points: Mapped[int] = mapped_column(Integer, default=0)
    top_scorer_points: Mapped[int] = mapped_column(Integer, default=0)
    is_calculated: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
