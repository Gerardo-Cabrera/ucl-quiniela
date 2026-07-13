import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Directorio con alembic.ini (backend/). El CLI resuelve `script_location` desde aquí.
_BACKEND_DIR = Path(__file__).resolve().parents[2]


def run_migrations() -> None:
    """Aplica las migraciones pendientes (`alembic upgrade head`) en un subproceso,
    igual que el comando de despliegue pero desde el arranque de la app: así el
    esquema existe aunque la plataforma (p. ej. Render) no ejecute alembic. Es
    idempotente (no hace nada si ya está en head) y lanza `CalledProcessError` si
    falla → el arranque falla rápido en vez de servir sin tablas.

    Subproceso (no in-process) a propósito: `alembic/env.py` corre en modo async
    (`asyncio.run`), que no puede invocarse dentro del event loop de la app."""
    logger.info("Aplicando migraciones (alembic upgrade head)...")
    subprocess.run(["alembic", "upgrade", "head"], cwd=_BACKEND_DIR, check=True)
    logger.info("Migraciones al día.")
