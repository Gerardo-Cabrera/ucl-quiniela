"""
Hashing de contraseñas con bcrypt directo (sustituye a passlib, sin mantenimiento).
Los hashes que passlib dejó en la BD ($2b$12$...) deben seguir verificando igual.
"""
import pytest
from httpx import AsyncClient

from app.core.security import hash_password, verify_password
from app.models.user import User
from tests.conftest import TestSessionLocal

# Generado con passlib 1.7.4 (CryptContext bcrypt, 12 rondas) para "testpass123".
PASSLIB_HASH = "$2b$12$6rH0cjKvlImBzt4F4.bCouA//SjDCxWZkVFUWIsDuLk9oViUnoaoq"


def test_roundtrip():
    h = hash_password("secreto123")
    assert h.startswith("$2b$12$")   # mismo formato y coste que passlib
    assert verify_password("secreto123", h) is True
    assert verify_password("secreto124", h) is False


def test_verifies_hashes_created_by_passlib():
    assert verify_password("testpass123", PASSLIB_HASH) is True
    assert verify_password("otra", PASSLIB_HASH) is False


def test_truncates_at_72_bytes_like_passlib():
    """bcrypt solo mira 72 bytes: una contraseña más larga verifica con su prefijo de
    72 bytes (comportamiento heredado de passlib; con bcrypt >= 5 y sin truncar
    explícitamente daría ValueError)."""
    long_pw = "á" * 50                            # 100 bytes UTF-8
    h = hash_password(long_pw)
    assert verify_password(long_pw, h) is True
    assert verify_password("á" * 36, h) is True   # mismos 72 primeros bytes
    assert verify_password("á" * 35, h) is False  # 70 bytes: distinta


def test_malformed_hash_is_not_valid():
    """Una fila con un hash que no es bcrypt (p. ej. 'x' sembrado en tests) no entra,
    y no revienta con 500."""
    assert verify_password("lo-que-sea", "x") is False


@pytest.mark.asyncio
async def test_login_with_passlib_hash(client: AsyncClient):
    """Integración: un usuario cuya contraseña hasheó passlib sigue pudiendo entrar."""
    async with TestSessionLocal() as session:
        session.add(User(team_name="Legacy FC", email="legacy@test.com", hashed_password=PASSLIB_HASH))
        await session.commit()
    resp = await client.post("/api/auth/login", json={"identifier": "legacy@test.com", "password": "testpass123"})
    assert resp.status_code == 200
