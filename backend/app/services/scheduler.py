"""
Cron jobs para sincronizar datos de UCL y calcular puntos automáticamente.
Se ejecuta en background al iniciar la aplicación.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from httpx import HTTPStatusError, RequestError
from app.database import AsyncSessionLocal
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.services import ucl_api
from app.services.scoring import calculate_match_points
from app.crud import player_crud, team_crud
from app.crud._upsert import upsert_by_key
from app.config import settings
import logging

logger = logging.getLogger(__name__)
# job_defaults en un solo sitio (no por-job): tolera corridas atrasadas y colapsa
# las acumuladas en una, en vez de que APScheduler las omita silenciosamente.
scheduler = AsyncIOScheduler(
    job_defaults={
        "misfire_grace_time": settings.JOB_MISFIRE_GRACE_SECONDS,
        "coalesce": True,
    },
)

# Marca temporal del último fetch de fixtures con éxito (pacing del sync adaptativo).
_last_fixtures_fetch: datetime | None = None


async def _retry(coro_func, job_name: str) -> tuple[bool, object]:
    """Ejecuta una coroutine con reintentos en caso de fallo. Devuelve
    `(ok, resultado)`: ok=False si agota los reintentos; resultado es lo que
    retorne la coroutine (los callers que no lo necesitan ignoran el retorno)."""
    max_retries = settings.JOB_MAX_RETRIES
    retry_delay = settings.JOB_RETRY_DELAY_SECONDS
    for attempt in range(1, max_retries + 1):
        try:
            return True, await coro_func()
        except (HTTPStatusError, RequestError) as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            # 401/403 = problema de credenciales/config, no transitorio: reintentar
            # es inútil y gasta cuota. Se corta con un mensaje accionable.
            if status in (401, 403):
                logger.error(
                    "Job %s: API-Football rechazó la petición con %d. Revisa "
                    "API_FOOTBALL_KEY y API_FOOTBALL_PROVIDER (key inválida/no "
                    "suscrita, o provider/host que no corresponden a la key). No se reintenta.",
                    job_name, status,
                )
                return False, None
            logger.warning(
                "Job %s attempt %d/%d failed (network): %s",
                job_name, attempt, max_retries, str(e),
            )
        except SQLAlchemyError as e:
            logger.warning(
                "Job %s attempt %d/%d failed (database): %s",
                job_name, attempt, max_retries, str(e),
            )
        except Exception as e:
            logger.error(
                "Job %s attempt %d/%d failed (unexpected): %s",
                job_name, attempt, max_retries, str(e),
                exc_info=True,
            )
        if attempt < max_retries:
            await asyncio.sleep(retry_delay * attempt)
    logger.error("Job %s failed after %d retries.", job_name, max_retries)
    return False, None


async def _do_sync_fixtures() -> list[int]:
    """Upsert de fixtures. Devuelve los ids de partidos que pasaron a FINISHED en
    esta corrida (para puntuarlos de inmediato tras el pitazo final)."""
    fixtures = await ucl_api.fetch_fixtures()
    # parse_fixture devuelve None para la fase previa (clasificación): se descarta,
    # la quiniela solo cubre de la fase de liga en adelante.
    parsed = [p for f in fixtures if (p := ucl_api.parse_fixture(f)) is not None]
    skipped = len(fixtures) - len(parsed)
    if skipped:
        logger.info("Omitidos %d fixtures de fase previa.", skipped)
    newly_finished: list[int] = []

    def _detect_finish(match: Match, row: dict) -> None:
        if match.status != MatchStatus.FINISHED and row["status"] == MatchStatus.FINISHED:
            newly_finished.append(match.id)

    async with AsyncSessionLocal() as db:
        # Upsert por api_fixture_id en UNA query (antes: 1 SELECT por fixture).
        # parse_fixture no incluye los campos de primer gol, así que el upsert no
        # pisa lo que resuelve el job de goles.
        count = await upsert_by_key(db, Match, parsed, "api_fixture_id", on_update=_detect_finish)
        await db.commit()
    logger.info("Synced %d fixtures.", count)
    return newly_finished


async def _has_match_in_play(now: datetime) -> bool:
    """Hay un partido 'en juego' = kickoff ya pasado y aún sin finalizar (ni pospuesto)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match.id)
            .where(
                Match.match_date <= now,
                Match.status.notin_([MatchStatus.FINISHED, MatchStatus.POSTPONED]),
            )
            .limit(1)
        )
        return result.first() is not None


async def sync_fixtures():
    """Sync ADAPTATIVO (job programado): corre cada SYNC_FIXTURES_MINUTES pero solo
    llama a la API si hay un partido EN JUEGO (marcador/estado casi en vivo) o si
    venció el respaldo SYNC_FIXTURES_IDLE_MINUTES. Tras un sync con éxito resuelve el
    primer gol y, si algún partido acaba de finalizar, puntúa de inmediato."""
    global _last_fixtures_fetch
    now = datetime.now(timezone.utc)
    in_play = await _has_match_in_play(now)
    idle_due = (
        _last_fixtures_fetch is None
        or now - _last_fixtures_fetch >= timedelta(minutes=settings.SYNC_FIXTURES_IDLE_MINUTES)
    )
    if not (in_play or idle_due):
        return
    logger.info("Starting fixture sync...")
    ok, newly_finished = await _retry(_do_sync_fixtures, "sync_fixtures")
    if ok:
        # Solo avanza el reloj de pacing si el fetch tuvo éxito (si falló, idle_due
        # sigue activo y se reintenta en la próxima corrida con datos frescos).
        _last_fixtures_fetch = now
        # Primer gol a la cadencia del sync: un partido en vivo que marca obtiene su
        # goleador sin esperar al timer horario. Barato: salta los ya resueltos.
        await _retry(_do_sync_first_goals, "sync_first_goals")
        if newly_finished:
            logger.info("Partido(s) recién finalizado(s): puntuando tras el pitazo final.")
            await _retry(_do_calculate_points, "calculate_pending_points")


async def sync_ucl_fixtures():
    """Sync forzado (endpoint admin /matches/sync): siempre corre, sin el gating
    adaptativo del job programado."""
    logger.info("Starting manual fixture sync...")
    await _retry(_do_sync_fixtures, "sync_ucl_fixtures")


async def _do_sync_teams():
    # Los clubes solo se guardan cuando la competición ya existe en BD (fase de liga
    # en adelante): sin partidos oficiales el selector del Top 8 queda vacío y no se
    # gasta cuota de la API durante la fase previa.
    async with AsyncSessionLocal() as db:
        has_matches = (await db.execute(select(Match.id).limit(1))).first() is not None
    if not has_matches:
        logger.info("Sync de clubes omitido: aún no hay partidos oficiales en BD.")
        return
    teams = await ucl_api.fetch_teams()
    parsed = [ucl_api.parse_team(t) for t in teams]
    async with AsyncSessionLocal() as db:
        count = await team_crud.upsert_many(db, parsed)
        await db.commit()
    logger.info("Synced %d teams.", count)


async def sync_teams():
    """Sincroniza los clubes participantes de la UCL desde API-Football (para el Top 8).
    Se ejecuta cada 24 h y al arrancar; los clubes casi no cambian en la temporada."""
    logger.info("Starting teams sync...")
    await _retry(_do_sync_teams, "sync_teams")


async def _do_sync_players():
    # Las plantillas se traen por equipo. Los ids de equipo salen de los partidos
    # ya sincronizados (no hay tabla de equipos). Una petición /players/squads por
    # equipo, acotada con un semáforo para no saturar la API.
    async with AsyncSessionLocal() as db:
        home = await db.execute(
            select(Match.home_team_api_id).where(Match.home_team_api_id.is_not(None))
        )
        away = await db.execute(
            select(Match.away_team_api_id).where(Match.away_team_api_id.is_not(None))
        )
        team_ids = {r[0] for r in home.all()} | {r[0] for r in away.all()}

    if not team_ids:
        logger.info("Synced 0 players (no hay equipos con id en BD todavía).")
        return

    semaphore = asyncio.Semaphore(5)

    async def fetch_one(team_api_id: int) -> list[dict]:
        async with semaphore:
            return await ucl_api.fetch_squad(team_api_id)

    squads = await asyncio.gather(
        *(fetch_one(tid) for tid in team_ids),
        return_exceptions=True,
    )
    parsed: list[dict] = []
    for team_api_id, squad in zip(team_ids, squads):
        if isinstance(squad, Exception):
            logger.warning("No se pudo obtener la plantilla del equipo %s: %s", team_api_id, squad)
            continue
        for entry in squad:
            parsed.extend(ucl_api.parse_squad(entry))

    async with AsyncSessionLocal() as db:
        count = await player_crud.upsert_many(db, parsed)
        await db.commit()
    logger.info("Synced %d players.", count)


async def sync_players():
    """Sincroniza las plantillas (jugadores) de los equipos desde API-Football.
    Se ejecuta cada 24 horas (y al arrancar)."""
    logger.info("Starting players sync...")
    await _retry(_do_sync_players, "sync_players")


async def _do_sync_first_goals():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match).where(
                Match.status == MatchStatus.FINISHED,
                Match.first_goal_team.is_(None),
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
                # Partidos 0-0 no tienen primer gol: no consultar eventos.
                (Match.home_score + Match.away_score) > 0,
            )
        )
        matches = result.scalars().all()

        semaphore = asyncio.Semaphore(5)

        async def fetch_events(fixture_id: int) -> list[dict]:
            async with semaphore:
                return await ucl_api.fetch_fixture_events(fixture_id)

        events_per_match = await asyncio.gather(
            *(fetch_events(m.api_fixture_id) for m in matches),
            return_exceptions=True,
        )
        updated = 0
        for match, events in zip(matches, events_per_match):
            if isinstance(events, Exception):
                logger.warning(
                    "No se pudieron obtener eventos del fixture %s: %s",
                    match.api_fixture_id, events,
                )
                continue
            scorer = ucl_api.get_first_goal_scorer(events)
            if scorer is None:
                continue
            match.first_goal_team = scorer["team"]
            match.first_goal_player_id = scorer["player_id"]
            match.first_goal_player = scorer["player_name"]
            updated += 1
            # Auto-reparación: si alguna predicción ya fue puntuada sin este
            # dato (p.ej. por el plazo de gracia), se recalcula en el próximo job.
            await db.execute(
                update(Prediction)
                .where(
                    Prediction.match_id == match.id,
                    Prediction.is_calculated == True,  # noqa: E712
                )
                .values(is_calculated=False, points_earned=0)
            )

        await db.commit()
        logger.info("Updated first goals for %d matches.", updated)


async def sync_first_goals():
    """Para partidos finalizados sin primer gol, consulta eventos. Se ejecuta cada hora."""
    logger.info("Starting first goals sync...")
    await _retry(_do_sync_first_goals, "sync_first_goals")


async def _do_calculate_points():
    # No puntuar hasta conocer el primer gol (el sync de goles corre cada hora
    # y este job cada 30 min); si la API no lo entrega dentro del plazo de
    # gracia, se calcula sin él para no dejar puntos bloqueados.
    grace_cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.FIRST_GOAL_GRACE_HOURS
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Prediction)
            .join(Match)
            .where(
                Match.status == MatchStatus.FINISHED,
                Prediction.is_calculated == False,  # noqa: E712
                or_(
                    Match.first_goal_team.is_not(None),
                    # Partidos 0-0 no tienen primer gol que esperar.
                    (Match.home_score + Match.away_score) == 0,
                    Match.match_date < grace_cutoff,
                ),
            )
            .options(selectinload(Prediction.match))
        )
        predictions = result.scalars().all()

        for pred in predictions:
            match = pred.match
            if match.home_score is None or match.away_score is None:
                continue

            breakdown = calculate_match_points(
                predicted_home=pred.predicted_home,
                predicted_away=pred.predicted_away,
                predicted_first_goal_player_id=pred.first_goal_player_id,
                actual_home=match.home_score,
                actual_away=match.away_score,
                actual_first_goal_player_id=match.first_goal_player_id,
                phase=match.phase,
            )
            pred.points_earned = breakdown["total"]
            pred.is_calculated = True

        await db.commit()
        logger.info("Calculated points for %d predictions.", len(predictions))


async def calculate_pending_points():
    """Calcula puntos de predicciones de partidos finalizados. Se ejecuta cada 30 minutos."""
    logger.info("Starting points calculation...")
    await _retry(_do_calculate_points, "calculate_pending_points")


def start_scheduler():
    # next_run_time: primera ejecución al arrancar (IntervalTrigger solo
    # dispararía tras el primer intervalo), escalonada para que los fixtures
    # lleguen antes que goles/puntos y sin golpear la API en paralelo.
    now = datetime.now()
    # Fixtures: sync ADAPTATIVO — corre cada minuto pero solo llama a la API si hay
    # partido en juego o venció el respaldo (ver sync_fixtures). Near-real-time.
    scheduler.add_job(sync_fixtures,            IntervalTrigger(minutes=settings.SYNC_FIXTURES_MINUTES), id="sync_fixtures",   replace_existing=True, next_run_time=now)
    # Clubes participantes (para el Top 8): al arrancar y refresco diario.
    scheduler.add_job(sync_teams,               IntervalTrigger(hours=settings.SYNC_TEAMS_HOURS),        id="sync_teams",      replace_existing=True, next_run_time=now + timedelta(seconds=15))
    scheduler.add_job(sync_first_goals,         IntervalTrigger(hours=settings.SYNC_GOALS_HOURS),        id="sync_goals",      replace_existing=True, next_run_time=now + timedelta(seconds=30))
    scheduler.add_job(calculate_pending_points, IntervalTrigger(minutes=settings.CALC_POINTS_MINUTES),   id="calc_points",     replace_existing=True, next_run_time=now + timedelta(seconds=60))
    # Plantillas: tras los fixtures (necesita los ids de equipo), refresco diario.
    scheduler.add_job(sync_players,             IntervalTrigger(hours=settings.SYNC_SQUADS_HOURS),       id="sync_players",    replace_existing=True, next_run_time=now + timedelta(seconds=90))
    scheduler.start()
    logger.info("Scheduler started with 5 jobs.")


def stop_scheduler():
    scheduler.shutdown()
