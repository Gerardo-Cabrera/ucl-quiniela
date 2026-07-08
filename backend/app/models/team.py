from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Team(Base):
    """
    Club participante de la UCL en la temporada configurada, sincronizado desde
    API-Football (`/teams?league&season`). Es la fuente de verdad de los clubes
    para el selector y la validación del Top 8 (ya no se hardcodean).
    """
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    api_team_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
