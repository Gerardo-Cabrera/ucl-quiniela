from sqlalchemy import String, Integer, DateTime, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
import enum


class MatchPhase(str, enum.Enum):
    LEAGUE = "league"
    KNOCKOUT_PLAYOFFS = "knockout_playoffs"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINALS = "quarter_finals"
    SEMI_FINALS = "semi_finals"
    FINAL = "final"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    api_fixture_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    home_team: Mapped[str] = mapped_column(String(100))
    away_team: Mapped[str] = mapped_column(String(100))
    # IDs de API-Football de cada equipo: necesarios para traer sus plantillas.
    home_team_api_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_team_api_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_team_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    away_team_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Definición por penales (score.penalty de API-Football); None si no hubo tanda.
    # El marcador (home/away_score) mantiene el resultado del juego (empate).
    penalty_home: Mapped[int | None] = mapped_column(Integer, nullable=True)
    penalty_away: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minuto de juego en vivo (API-Football status.elapsed); None fuera de juego.
    elapsed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minutos de descuento en curso (status.extra): con elapsed 45/90 la tarjeta muestra
    # "45+2" / "90+3". En la prórroga elapsed sigue contando (91-120) y extra vuelve a None.
    elapsed_extra: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # status.short de API-Football tal cual (1H, HT, 2H, ET, BT, P, FT, AET, PEN, PST,
    # SUSP…). `status` lo resume en 4 estados; este detalle lo usa la tarjeta en vivo para
    # mostrar "Descanso" (HT), la pausa de la prórroga (BT), la tanda de penales (P) o un
    # partido suspendido/interrumpido en lugar de un minuto colgado (en HT la API deja
    # elapsed=45 hasta la reanudación).
    api_status: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # Primer gol del partido (resuelto por el job de eventos). `first_goal_team`
    # se conserva para mostrarlo; `first_goal_player_id`/`first_goal_player` son el
    # goleador real (el id es contra lo que se puntúa el pronóstico).
    first_goal_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_goal_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_goal_player: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Goles del partido (goleador + asistente; sin goles en propia ni penaltis fallados),
    # guardados al consultar los eventos para el primer gol. Base de los rankings de
    # goleadores/asistidores de la quiniela (fase de liga en adelante) sin cuota extra.
    goal_events: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)

    # Probabilidad de victoria PRE-partido según API-Football (`/predictions`, `percent`
    # local/empate/visitante en % enteros). Solo se consulta para el PRÓXIMO partido de
    # cada equipo (una petición por partido: cuota) y se refresca cada
    # SYNC_PROBABILITIES_HOURS mientras siga por jugarse. La tarjeta la muestra en
    # Partidos → Próximos; None si aún no se consultó o la API no la entrega.
    prob_home: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prob_draw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prob_away: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prob_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Jornada de la fase de liga (ronda 'League Stage - N' de la API); None en
    # eliminatorias. Agrupa los días (martes a jueves) en la "jornada completa".
    round_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phase: Mapped[MatchPhase] = mapped_column(SAEnum(MatchPhase), default=MatchPhase.LEAGUE)
    status: Mapped[MatchStatus] = mapped_column(SAEnum(MatchStatus), default=MatchStatus.SCHEDULED)

    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match", lazy="select")
