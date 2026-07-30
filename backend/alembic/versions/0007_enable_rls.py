"""Habilitar RLS en todas las tablas de `public` (hardening; aviso de Supabase)

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-30

Supabase expone el schema `public` vía su Data API (PostgREST); sin RLS, el rol
`anon` podría leer/escribir las tablas saltándose nuestro backend. Se activa RLS
(sin políticas = denegar por defecto a roles no propietarios). El backend conecta
como PROPIETARIO de las tablas, que BYPASSA RLS (no usamos FORCE), así que sigue
funcionando igual. También es defensa en profundidad fuera de Supabase.

DO dinámico: cubre todas las tablas actuales de `public` (incluida
`alembic_version`) sin una lista que mantener. Idempotente: activar RLS ya activo
es no-op. Solo corre en Postgres (los tests usan SQLite vía metadata, sin Alembic).
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _set_rls(action: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE t text;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP
                EXECUTE format('ALTER TABLE public.%I {action} ROW LEVEL SECURITY', t);
            END LOOP;
        END $$;
        """
    )


def upgrade() -> None:
    _set_rls("ENABLE")


def downgrade() -> None:
    _set_rls("DISABLE")
