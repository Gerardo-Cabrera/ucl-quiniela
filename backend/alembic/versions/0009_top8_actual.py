"""app_state.top8_actual: el Top 8 real con el que se puntuó (constancia y aciertos)

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_state", sa.Column("top8_actual", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_state", "top8_actual")
