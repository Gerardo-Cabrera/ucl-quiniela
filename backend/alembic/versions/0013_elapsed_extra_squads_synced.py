"""matches.elapsed_extra (descuento en vivo) y app_state.squads_synced_at

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("elapsed_extra", sa.Integer(), nullable=True))
    op.add_column("app_state", sa.Column("squads_synced_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("app_state", "squads_synced_at")
    op.drop_column("matches", "elapsed_extra")
