"""
Tests del parseo de configuración (CORS_ORIGINS y API-Football).
Regresión: con List[str], pydantic-settings exigía JSON en el .env y el
formato simple (http://localhost:5173) rompía el arranque de la app.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_cors_single_origin():
    s = Settings(CORS_ORIGINS="http://localhost:5173")
    assert s.cors_origins_list == ["http://localhost:5173"]


def test_cors_comma_separated():
    s = Settings(CORS_ORIGINS="http://localhost:5173, https://miapp.com")
    assert s.cors_origins_list == ["http://localhost:5173", "https://miapp.com"]


def test_cors_json_format_backwards_compatible():
    s = Settings(CORS_ORIGINS='["http://localhost:5173", "https://miapp.com"]')
    assert s.cors_origins_list == ["http://localhost:5173", "https://miapp.com"]


def test_cors_plain_env_var_does_not_crash(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com")
    s = Settings()
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]


def test_provider_autodetected_from_key_length():
    """Solo importa la key: 32 chars → api-sports; más larga → RapidAPI."""
    assert Settings(API_FOOTBALL_PROVIDER="auto", API_FOOTBALL_KEY="a" * 32).football_provider == "apisports"
    assert Settings(API_FOOTBALL_PROVIDER="auto", API_FOOTBALL_KEY="a" * 50).football_provider == "rapidapi"


def test_provider_explicit_override_wins():
    assert Settings(API_FOOTBALL_PROVIDER="rapidapi", API_FOOTBALL_KEY="a" * 32).football_provider == "rapidapi"


def test_api_football_key_required_in_production():
    with pytest.raises(ValidationError):
        Settings(APP_ENV="production", SECRET_KEY="x" * 32, API_FOOTBALL_KEY="")
    # Con key definida no lanza.
    Settings(APP_ENV="production", SECRET_KEY="x" * 32, API_FOOTBALL_KEY="k" * 32)
