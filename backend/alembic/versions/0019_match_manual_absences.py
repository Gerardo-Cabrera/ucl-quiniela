"""Correcciones manuales de disponibilidad por partido (admin)

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-24

`matches.manual_absences`: lo que el admin corrige a mano sobre la disponibilidad de un
jugador para ese partido (baja que el proveedor aún no ha registrado, o al revés: un
jugador que sí puede jugar). Va aparte de `absences` porque el job de bajas reemplaza
esa lista en cada corrida, y una corrección manual debe sobrevivirle.

Aditiva: una columna JSON anulable, sin tocar datos existentes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("manual_absences", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "manual_absences")
