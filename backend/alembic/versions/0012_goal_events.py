"""matches.goal_events (goles por partido); baja de app_state.top_scorers/top_assists

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-09

Los rankings de goleadores/asistidores pasan a calcularse de los goles guardados
por partido (solo partidos de la quiniela: fase de liga en adelante), en vez de
`/players/topscorers`, que incluye la fase previa.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("goal_events", sa.JSON(), nullable=True))
    op.drop_column("app_state", "top_assists")
    op.drop_column("app_state", "top_scorers")


def downgrade() -> None:
    op.add_column("app_state", sa.Column("top_scorers", sa.JSON(), nullable=True))
    op.add_column("app_state", sa.Column("top_assists", sa.JSON(), nullable=True))
    op.drop_column("matches", "goal_events")
