from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

# Cada viaje a la BD cuesta lo que tarde la red entre el backend y PostgreSQL: en
# producción (Render ↔ Supabase) son decenas de milisegundos POR VIAJE, y una petición
# no hace solo sus consultas. Con el engine transaccional de siempre, cada request pagaba
# además 5 viajes fijos: el pre-ping (BEGIN + ";" + ROLLBACK, así lo hace el dialecto
# asyncpg fuera de autocommit), el BEGIN y el COMMIT. `GET /config/teams` eran 6 viajes
# para UNA consulta; `GET /matches`, 9 para 4.
#
# Por eso el pool nace en AUTOCOMMIT (el pre-ping pasa a ser 1 viaje) y se exponen dos
# fábricas de sesiones sobre ESE MISMO pool:
#   - ReadOnlySessionLocal: autocommit, sin BEGIN/COMMIT. Para los GET (solo lectura).
#   - AsyncSessionLocal: transaccional (READ COMMITTED, como antes). Para todo lo que
#     escribe: POST/PUT/PATCH/DELETE y los jobs del scheduler. Atomicidad y rollback
#     intactos.
# SQLAlchemy devuelve la conexión al nivel del pool (autocommit) al soltarla, así que
# alternar ambas fábricas sobre la misma conexión es seguro.
engine = create_async_engine(
    settings.DATABASE_URL,
    isolation_level="AUTOCOMMIT",
    # Sin echo=True: añadía un handler propio a sqlalchemy.engine.Engine y cada
    # sentencia salía dos veces (su handler + el raíz). El eco SQL se controla con
    # SQL_ECHO en app/core/logging.py (un solo formato, un solo handler).
    # pool_pre_ping: descarta conexiones muertas al sacarlas del pool.
    # pool_recycle: además, no reutiliza conexiones de más de 5 min. El pooler de
    # Supabase (pgbouncer) cierra las conexiones ociosas y el keep-alive solo pinga
    # /health (no toca la BD), así que el pool puede quedar inactivo entre logins;
    # reciclar evita que el primer login tras un rato use una conexión ya obsoleta.
    pool_pre_ping=True,
    pool_recycle=300,
)

# Mismo pool, pero cada conexión que entrega abre transacción (BEGIN ... COMMIT).
_transactional_engine = engine.execution_options(isolation_level="READ COMMITTED")

AsyncSessionLocal = async_sessionmaker(
    _transactional_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

ReadOnlySessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Sesión del request. Los GET reciben una de solo lectura en autocommit (sin
    BEGIN/COMMIT: dos viajes menos a la BD por petición); el resto de métodos, una
    transaccional que confirma al terminar y revierte si el endpoint falla.

    Regla que sostiene esto: **un GET no escribe**. En autocommit cada sentencia se
    confirma sola, así que un GET que escribiera perdería la atomicidad sin avisar."""
    factory = ReadOnlySessionLocal if request.method == "GET" else AsyncSessionLocal
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
