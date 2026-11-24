"""Tarjetas y bajas por partido (marcas del selector de jugadores)

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-23

- `matches.card_events`: tarjetas del partido (amarilla/roja por jugador), guardadas al
  finalizar a partir de los mismos eventos que ya se descargan para el primer gol. De
  ellas se deduce quién está sancionado en el partido siguiente (expulsión o ciclo de
  amarillas), que la API no siempre informa. Los partidos ya finalizados se rellenan
  solos tras el primer arranque (una petición por partido, espaciadas).
- `matches.absences`: bajas del partido según API-Football (`/injuries`): lesionados,
  sancionados por roja, dudas y jugadores fuera de la lista. Las rellena el job de bajas.

Aditiva: dos columnas JSON anulables, sin tocar datos existentes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("card_events", sa.JSON(), nullable=True))
    op.add_column("matches", sa.Column("absences", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "absences")
    op.drop_column("matches", "card_events")
