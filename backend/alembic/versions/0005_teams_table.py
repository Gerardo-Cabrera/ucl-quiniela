"""Tabla teams: clubes UCL sincronizados desde API-Football (para el Top 8)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_team_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"])
    op.create_index(op.f("ix_teams_api_team_id"), "teams", ["api_team_id"], unique=True)
    op.create_index(op.f("ix_teams_name"), "teams", ["name"])


def downgrade() -> None:
    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_index(op.f("ix_teams_api_team_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_table("teams")
