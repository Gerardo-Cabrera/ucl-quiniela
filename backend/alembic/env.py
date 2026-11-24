import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base
# Importar el paquete registra TODOS los modelos en Base.metadata (autogenerate y
# `alembic check` los necesitan completos; importar solo algunos nombres funcionaba por
# efecto colateral del __init__ y daba a entender que el resto no contaba).
import app.models  # noqa: F401
from app.config import settings

config = context.config
# Las migraciones corren en modo async (run_async_migrations): la URL debe
# conservar el driver asyncpg; con +psycopg2 create_async_engine falla.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


# Clave del candado de migraciones (arbitraria, fija; "UCL" en ASCII).
_MIGRATION_LOCK_KEY = 0x55434C


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        # Cada instancia aplica las migraciones al arrancar, y puede haber más de una
        # contra la misma BD (dos servicios, o un despliegue que arranca la versión nueva
        # con la anterior aún viva). Sin esto, dos arranques simultáneos leen la misma
        # revisión, ambos intentan el mismo ALTER TABLE y el segundo falla y aborta su
        # inicio. El candado (de transacción: se suelta solo al terminar) las pone en
        # fila ANTES de que Alembic lea la revisión actual: la segunda espera y, cuando
        # entra, ya no tiene nada que aplicar.
        if connection.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _MIGRATION_LOCK_KEY})
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
