from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import false, func
from app.database import Base


class AppState(Base):
    """Estado global de la aplicación en una fila única (id=1).

    Hoy solo guarda el interruptor de prórroga de pronósticos: cuando está activo,
    los pronósticos de una jornada siguen abiertos desde que vence el plazo normal
    (PREDICTION_LEAD_MINUTES antes del primer partido del día) hasta que ese primer
    partido arranca. Lo alterna un admin (ver routers/predictions).
    """
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
