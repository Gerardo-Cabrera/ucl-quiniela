"""Tabla tournament_predictions: MVP y máximo goleador del torneo (una fila por usuario)

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-01

RLS: 0007 activó RLS en las tablas existentes con un DO dinámico que ya corrió; una
tabla nueva NO queda cubierta, así que aquí se activa explícitamente sobre ella
(sin políticas = denegar por defecto; el backend conecta como PROPIETARIO y la
bypassa). Solo corre en Postgres vía Alembic (los tests usan SQLite vía metadata).
"""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tournament_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mvp_player_id", sa.Integer(), nullable=True),
        sa.Column("mvp_player", sa.String(length=100), nullable=True),
        sa.Column("top_scorer_player_id", sa.Integer(), nullable=True),
        sa.Column("top_scorer_player", sa.String(length=100), nullable=True),
        sa.Column("mvp_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("top_scorer_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_calculated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_tournament_predictions_id"), "tournament_predictions", ["id"])
    op.create_index(
        op.f("ix_tournament_predictions_user_id"), "tournament_predictions", ["user_id"], unique=True
    )
    op.execute("ALTER TABLE tournament_predictions ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("tournament_predictions")
