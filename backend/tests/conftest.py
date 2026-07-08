"""
Fixtures compartidos para tests de integración.
Usa una base de datos SQLite en memoria para aislamiento.
"""
import os

# Debe definirse ANTES de importar la app para que Settings lo lea.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.player import Player
from app.models.team import Team

# Plantillas mínimas para los tests (equipos usados en los partidos de prueba).
SEED_PLAYERS = [
    {"api_player_id": 10, "name": "Vinicius Jr",  "team_api_id": 541, "team_name": "Real Madrid", "position": "Attacker"},
    {"api_player_id": 11, "name": "Bellingham",   "team_api_id": 541, "team_name": "Real Madrid", "position": "Midfielder"},
    {"api_player_id": 20, "name": "Lewandowski",  "team_api_id": 529, "team_name": "Barcelona",   "position": "Attacker"},
    {"api_player_id": 21, "name": "Lamine Yamal", "team_api_id": 529, "team_name": "Barcelona",   "position": "Attacker"},
]

# Clubes (tabla teams, normalmente sincronizada desde la API) para validar el Top 8.
SEED_TEAMS = [
    {"api_team_id": i, "name": name}
    for i, name in enumerate([
        "Real Madrid", "Manchester City", "Bayern Munich", "Barcelona",
        "Arsenal", "Liverpool", "Inter Milan", "Paris Saint-Germain", "Juventus",
    ], start=1)
]

engine_test = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crea todas las tablas antes de cada test y las elimina después."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        session.add_all([Player(**p) for p in SEED_PLAYERS])
        session.add_all([Team(**t) for t in SEED_TEAMS])
        await session.commit()
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP asíncrono para testing de endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """Cliente autenticado: registra un usuario y retorna el client con token."""
    register_data = {
        "team_name": "Jax FC",
        "email": "test@test.com",
        "password": "testpass123",
    }
    await client.post("/api/auth/register", json=register_data)

    login_data = {"identifier": "test@test.com", "password": "testpass123"}
    login_resp = await client.post("/api/auth/login", json=login_data)
    token = login_resp.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def admin_client(auth_client: AsyncClient):
    """Cliente autenticado con privilegios de admin."""
    async with TestSessionLocal() as session:
        user = await session.get(User, 1)
        user.is_admin = True
        await session.commit()
    return auth_client
