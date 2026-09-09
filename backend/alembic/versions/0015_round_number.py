"""matches.round_number: jornada de la fase de liga (ronda de la API)

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-10

Se rellena con el siguiente sync de fixtures (upsert de todos los campos).
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("round_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "round_number")
