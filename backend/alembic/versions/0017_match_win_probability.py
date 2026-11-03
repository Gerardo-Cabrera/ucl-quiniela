"""matches.prob_home/draw/away + prob_updated_at: probabilidad de victoria pre-partido

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-03

Las rellena el job sync_win_probabilities (API-Football /predictions) para el próximo
partido de cada equipo; hasta entonces la tarjeta no muestra la barra.
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("prob_home", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("prob_draw", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("prob_away", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("prob_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "prob_updated_at")
    op.drop_column("matches", "prob_away")
    op.drop_column("matches", "prob_draw")
    op.drop_column("matches", "prob_home")
