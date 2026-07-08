from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    team_name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # Alias/nombre de usuario opcional (único si se indica). Sirve, junto al email
    # y al nombre de equipo, como identificador para iniciar sesión.
    alias: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="user", lazy="select")
    top8_picks: Mapped[list["Top8Pick"]] = relationship(back_populates="user", lazy="select")
