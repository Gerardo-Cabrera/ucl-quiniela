"""Recalcular los puntos de partidos: el marcador exacto ahora SUMA el resultado

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-10

Antes el exacto sustituía a victoria/empate (liga: 8); ahora se suman (8 + 5 = 13,
empate exacto 8 + 6 = 14). Las predicciones ya puntuadas se marcan como pendientes
y el job de puntos (al arrancar y cada CALC_POINTS_MINUTES) las recalcula con la
regla nueva; el resto de datos no cambia.
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

_RESET = "UPDATE predictions SET is_calculated = false, points_earned = 0, first_goal_points = 0 WHERE is_calculated"


def upgrade() -> None:
    op.execute(_RESET)


def downgrade() -> None:
    op.execute(_RESET)   # el job vuelve a puntuar con la regla del código desplegado
