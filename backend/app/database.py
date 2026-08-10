from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV == "development",
    # pool_pre_ping: descarta conexiones muertas al sacarlas del pool.
    # pool_recycle: además, no reutiliza conexiones de más de 5 min. El pooler de
    # Supabase (pgbouncer) cierra las conexiones ociosas y el keep-alive solo pinga
    # /health (no toca la BD), así que el pool puede quedar inactivo entre logins;
    # reciclar evita que el primer login tras un rato use una conexión ya obsoleta.
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
