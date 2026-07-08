"""Alias opcional de usuario (identificador de login adicional)

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-05
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("alias", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_users_alias"), "users", ["alias"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_alias"), table_name="users")
    op.drop_column("users", "alias")
