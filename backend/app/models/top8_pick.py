from sqlalchemy import Integer, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Top8Pick(Base):
    __tablename__ = "top8_picks"
    __table_args__ = (
        UniqueConstraint("user_id", "position", name="uq_top8_user_position"),
        UniqueConstraint("user_id", "team_name", name="uq_top8_user_team"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Posición pronosticada en el Top 8 (1-8, obligatoria)
    position: Mapped[int] = mapped_column(Integer)
    team_name: Mapped[str] = mapped_column(String(100))

    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    is_calculated: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="top8_picks")
