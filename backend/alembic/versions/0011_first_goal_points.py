"""predictions.first_goal_points: desglose del primer gol (visible en la tarjeta)

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column("first_goal_points", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("predictions", "first_goal_points")
