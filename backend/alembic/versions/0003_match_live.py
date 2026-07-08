"""Datos de partido en vivo: minuto de juego y definición por penales

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("penalty_home", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("penalty_away", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("elapsed", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "elapsed")
    op.drop_column("matches", "penalty_away")
    op.drop_column("matches", "penalty_home")
