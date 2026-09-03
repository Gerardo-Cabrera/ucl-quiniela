"""app_state.top_scorers / top_assists: rankings de la temporada (vista Torneo)

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_state", sa.Column("top_scorers", sa.JSON(), nullable=True))
    op.add_column("app_state", sa.Column("top_assists", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_state", "top_assists")
    op.drop_column("app_state", "top_scorers")
