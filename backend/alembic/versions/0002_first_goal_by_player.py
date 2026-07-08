"""Primer gol por jugador: tabla players, ids de equipo y goleador en matches/predictions

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabla de jugadores (plantillas sincronizadas desde API-Football).
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_player_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("team_api_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("position", sa.String(length=30), nullable=True),
        sa.Column("photo", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_players_id"), "players", ["id"])
    op.create_index(op.f("ix_players_api_player_id"), "players", ["api_player_id"], unique=True)
    op.create_index(op.f("ix_players_team_api_id"), "players", ["team_api_id"])
    op.create_index(op.f("ix_players_team_name"), "players", ["team_name"])

    # matches: ids de equipo (para traer plantillas) y goleador del primer gol.
    op.add_column("matches", sa.Column("home_team_api_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("away_team_api_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("first_goal_player_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("first_goal_player", sa.String(length=100), nullable=True))

    # predictions: el primer gol pasa de equipo (texto) a jugador (id + nombre).
    op.add_column("predictions", sa.Column("first_goal_player_id", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("first_goal_player", sa.String(length=100), nullable=True))
    op.drop_column("predictions", "first_goal_team")


def downgrade() -> None:
    op.add_column("predictions", sa.Column("first_goal_team", sa.String(length=100), nullable=True))
    op.drop_column("predictions", "first_goal_player")
    op.drop_column("predictions", "first_goal_player_id")

    op.drop_column("matches", "first_goal_player")
    op.drop_column("matches", "first_goal_player_id")
    op.drop_column("matches", "away_team_api_id")
    op.drop_column("matches", "home_team_api_id")

    op.drop_index(op.f("ix_players_team_name"), table_name="players")
    op.drop_index(op.f("ix_players_team_api_id"), table_name="players")
    op.drop_index(op.f("ix_players_api_player_id"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_table("players")
