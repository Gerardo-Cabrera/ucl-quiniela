from datetime import datetime
from sqlalchemy import JSON, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import false, func
from app.database import Base


class AppState(Base):
    """Estado global de la aplicación en una fila única (id=1).

    - `prediction_override`: interruptor de prórroga de pronósticos. Activo, los
      pronósticos de una jornada siguen abiertos desde que vence el plazo normal
      (PREDICTION_LEAD_MINUTES antes del primer partido del día) hasta que ese
      primer partido arranca. Lo alterna un admin (ver routers/predictions).
    - `top8_actual`: el Top 8 REAL (8 nombres ordenados 1.º-8.º) con el que se
      puntuaron los picks; null hasta calcularse. Constancia de cómo quedó la fase
      de liga y base para mostrar los aciertos de cada usuario.
    - `squads_synced_at`: cuándo se sincronizaron por última vez las plantillas
      (~36 peticiones). Al arrancar, si es reciente, el job espera al vencimiento en
      vez de repetirlas (recargas en desarrollo, redeploys).
    """
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=false(), default=False
    )
    top8_actual: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    squads_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
