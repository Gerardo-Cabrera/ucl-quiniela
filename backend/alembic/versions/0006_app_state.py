"""Tabla app_state: estado global (fila única) — interruptor de prórroga de pronósticos

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # Siembra la fila única (id=1) para que el estado exista desde el arranque.
    op.execute("INSERT INTO app_state (id, prediction_override) VALUES (1, false)")


def downgrade() -> None:
    op.drop_table("app_state")
