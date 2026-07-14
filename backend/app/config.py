import json
from zoneinfo import ZoneInfo
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://quiniela:quiniela_pass@localhost:5432/ucl_quiniela"

    # Security
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # API-Football: hay dos formas de acceder a la MISMA API con distinta
    # autenticación (RapidAPI o api-sports directo). Lo ÚNICO que hay que
    # configurar es la key (obligatoria en producción); el proveedor se deduce
    # solo de la key: las de api-sports tienen 32 caracteres y las de RapidAPI son
    # más largas (~50). API_FOOTBALL_PROVIDER queda como override opcional.
    API_FOOTBALL_KEY: str = ""
    API_FOOTBALL_PROVIDER: str = "auto"  # opcional: auto (por defecto) | apisports | rapidapi
    API_FOOTBALL_TIMEOUT: float = 30.0
    UCL_LEAGUE_ID: int = 2
    # Temporada de la competición (año de inicio: 2026 = 2026/27). Si se deja en 0,
    # el sistema la IDENTIFICA automáticamente vía API (la marcada como `current`).
    UCL_SEASON: int = 2026
    SYNC_TEAMS_HOURS: int = 24
    # Zona horaria para agrupar partidos por "jornada" (día) en la vista de MVPs.
    # Agrupar en UTC partiría un partido nocturno europeo en dos días. IANA (zoneinfo).
    TOURNAMENT_TZ: str = "Europe/Madrid"
    # Plazo de envío de pronósticos: cierran estos minutos antes del PRIMER partido
    # del día (jornada). El interruptor admin de prórroga (AppState.prediction_override)
    # reabre los pronósticos desde ese plazo hasta que arranca ese primer partido.
    PREDICTION_LEAD_MINUTES: int = 60

    # Scheduler intervals.
    # Sync de fixtures ADAPTATIVO (ver sync_fixtures): la tarea corre cada
    # SYNC_FIXTURES_MINUTES pero solo llama a la API si hay un partido EN JUEGO
    # (marcador/estado casi en vivo) o si pasó el respaldo SYNC_FIXTURES_IDLE_MINUTES
    # (captar kickoffs y fixtures nuevos). Fuera de los partidos no malgasta cuota.
    SYNC_FIXTURES_MINUTES: int = 1
    SYNC_FIXTURES_IDLE_MINUTES: int = 30
    SYNC_GOALS_HOURS: int = 1
    SYNC_SQUADS_HOURS: int = 24
    CALC_POINTS_MINUTES: int = 30
    # Fallback: si un partido de fase de liga sigue LIVE pasados estos minutos desde
    # el kickoff, se da por finalizado (135 = 90' + descanso + añadido + margen). No
    # aplica a eliminatorias (prórroga/penales pueden superarlo).
    MATCH_FINISH_FALLBACK_MINUTES: int = 135
    JOB_MAX_RETRIES: int = 3
    JOB_RETRY_DELAY_SECONDS: int = 10
    # Plazo para ejecutar una corrida atrasada (reload, loop ocupado) en vez de
    # descartarla: sin esto APScheduler la omite si el tick no dispara en 1 s.
    JOB_MISFIRE_GRACE_SECONDS: int = 3600

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "60/minute"
    # Límite más estricto para /auth/* (login y registro): frena ataques de
    # fuerza bruta de credenciales sin molestar al uso legítimo.
    RATE_LIMIT_AUTH: str = "10/minute"
    # Endpoints admin de sync manual: cada llamada consume cuota de API-Football;
    # tope holgado para re-syncs legítimos que frena ráfagas de clics/scripts.
    RATE_LIMIT_SYNC: str = "10/hour"

    # Scoring: si tras este plazo la API no entrega el primer gol de un partido
    # finalizado, se calculan los puntos sin ese dato para no bloquearlos.
    FIRST_GOAL_GRACE_HOURS: int = 48

    # Game rules
    TOP8_PICK_COUNT: int = 8

    # App
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    # str (no List[str]): pydantic-settings exige JSON en env vars para tipos
    # complejos y rompería el arranque con el formato simple del .env.
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def tournament_tz(self) -> ZoneInfo:
        """Zona horaria del torneo para agrupar por jornada (ZoneInfo cachea la
        instancia). Fuente única para routers y CRUD."""
        return ZoneInfo(self.TOURNAMENT_TZ)

    @property
    def cors_origins_list(self) -> list[str]:
        """Acepta lista separada por comas o JSON: ambos formatos de .env funcionan."""
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                return [str(origin) for origin in json.loads(raw)]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def football_provider(self) -> str:
        """Proveedor efectivo. Si no se fuerza (valor por defecto 'auto'), se
        deduce de la KEY: las de api-sports tienen 32 caracteres y las de RapidAPI
        son más largas. Así basta con configurar API_FOOTBALL_KEY."""
        provider = self.API_FOOTBALL_PROVIDER.strip().lower()
        if provider in ("apisports", "rapidapi"):
            return provider
        return "apisports" if len(self.API_FOOTBALL_KEY.strip()) == 32 else "rapidapi"

    @property
    def football_base_url(self) -> str:
        """URL base v3 según el proveedor."""
        if self.football_provider == "rapidapi":
            return "https://api-football-v1.p.rapidapi.com/v3"
        return "https://v3.football.api-sports.io"

    @property
    def football_headers(self) -> dict[str, str]:
        """Cabeceras de autenticación según el proveedor."""
        if self.football_provider == "rapidapi":
            return {
                "X-RapidAPI-Key": self.API_FOOTBALL_KEY,
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
            }
        return {"x-apisports-key": self.API_FOOTBALL_KEY}

    # Normaliza el driver de la URL de la BD a asyncpg: los proveedores gestionados
    # (p. ej. Supabase, Render) entregan la cadena como 'postgresql://...' o
    # 'postgres://...', pero el engine async usa 'postgresql+asyncpg://'. Se hace
    # strip() primero: un espacio/salto de línea en el .env saltaría el startswith
    # dejando un driver sync que rompería la conexión.
    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg_driver(cls, v: str) -> str:
        v = v.strip()
        if v.startswith(("postgres://", "postgresql://")):
            v = "postgresql+asyncpg://" + v.split("://", 1)[1]
        return v

    @model_validator(mode="after")
    def _check_production_config(self) -> "Settings":
        if self.APP_ENV == "production":
            if self.SECRET_KEY == INSECURE_SECRET_KEY:
                raise ValueError(
                    "SECRET_KEY inseguro: define un SECRET_KEY propio en producción (.env)."
                )
            if not self.API_FOOTBALL_KEY.strip():
                raise ValueError(
                    "API_FOOTBALL_KEY es obligatoria en producción (sin ella no hay datos de la UCL)."
                )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
