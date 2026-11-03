"""matches.api_status: status.short de API-Football (HT, BT, P… para el reloj en vivo)

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-03

Se rellena con el siguiente sync de fixtures (upsert de todos los campos); hasta
entonces la tarjeta en vivo sigue mostrando el minuto, como antes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("api_status", sa.String(length=8), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "api_status")
