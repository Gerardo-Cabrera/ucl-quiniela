from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.database import get_db
from app.routers import (
    auth_router,
    matches_router,
    predictions_router,
    leaderboard_router,
    top8_router,
    config_router,
    stats_router,
    matchdays_router,
    tournament_router,
)
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.ucl_api import close_client
from app.core.migrations import run_migrations
import asyncio
import logging
import time

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("UCL Quiniela API iniciando...")
    # Asegura el esquema (crea/actualiza tablas) antes de arrancar el scheduler:
    # así los jobs no fallan con "relation ... does not exist" si el despliegue
    # no ejecutó las migraciones (p. ej. Render). En un hilo: alembic corre async.
    try:
        await asyncio.to_thread(run_migrations)
    except Exception:
        logger.exception("Fallo aplicando migraciones al arrancar; se aborta el inicio.")
        raise
    if settings.SCHEDULER_ENABLED:
        await start_scheduler()
    else:
        logger.warning(
            "Scheduler DESACTIVADO (SCHEDULER_ENABLED=false): esta instancia no sincroniza "
            "con API-Football ni calcula puntos; debe hacerlo otra contra la misma BD."
        )
    yield
    if settings.SCHEDULER_ENABLED:
        stop_scheduler()
    await close_client()
    logger.info("UCL Quiniela API detenida.")


app = FastAPI(
    title="UCL Quiniela API",
    description="API para la quiniela de UEFA Champions League",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Compresión de respuestas de más de 1 KB cuando el cliente la acepta: /matches pesa
# ~87 KB sin comprimir (~6 KB con gzip) y cada participante lo refresca cada minuto,
# muchas veces desde el móvil; /tournament/players, ~180 KB. En Render no hay nginx
# delante del API (solo en el modo compose de producción), así que comprime el backend.
# Se registra PRIMERO (= el más interno, pegado a la app): add_middleware antepone, y si
# quedara por fuera de SlowAPIMiddleware (un BaseHTTPMiddleware que reemite las respuestas
# en streaming sin Content-Length) comprimiría también las pequeñas, ignorando el mínimo.
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # El frontend vive en otro origen y cada petición lleva Authorization, así que el
    # navegador hace antes un preflight (OPTIONS) por URL y lo cachea este tiempo. Con
    # los 10 min por defecto, una vista que refresca cada minuto repetía el preflight
    # (un viaje extra al servidor) una de cada diez veces; 2 h es el tope que respeta
    # Chrome (Firefox admite más).
    max_age=7200,
)

# Rutas
app.include_router(auth_router,        prefix="/api")
app.include_router(matches_router,     prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")
app.include_router(top8_router,        prefix="/api")
app.include_router(config_router,      prefix="/api")
app.include_router(stats_router,       prefix="/api")
app.include_router(matchdays_router,   prefix="/api")
app.include_router(tournament_router,  prefix="/api")


@app.get("/", tags=["Health"])
async def root():
    return {
        "app":     "UCL Quiniela API",
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


# Diagnóstico puntual, público y que toma una conexión del pool: unas pocas llamadas por
# minuto e IP bastan (el límite global, 120/min, es para las vistas que refrescan solas).
_HEALTH_DB_RATE_LIMIT = "10/minute"


@app.get("/health/db", tags=["Health"])
@limiter.limit(_HEALTH_DB_RATE_LIMIT)
async def health_db(request: Request, db: AsyncSession = Depends(get_db)):
    """Comprueba la BD y mide lo que tarda UN viaje de ida y vuelta (un `SELECT 1`).
    Ese número multiplica el tiempo de cada petición (una hace varios viajes), así que
    es el dato para decidir si el backend y la BD están lo bastante cerca: unos pocos
    ms en la misma región, decenas si están en regiones distintas. `/health` sigue sin
    tocar la BD: es el que deben usar el keep-alive y los monitores."""
    await db.execute(text("SELECT 1"))   # calienta: conexión del pool y sentencia preparada
    start = time.perf_counter()
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "db_roundtrip_ms": round((time.perf_counter() - start) * 1000, 1)}
