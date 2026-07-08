"""Ventana de envío de pronósticos (plazo por jornada + interruptor de prórroga).

Fuente ÚNICA de la regla, tanto para validar el POST como para anotar el flag
`predictable` que consume el frontend (sin reimplementar zonas horarias en TS):

  plazo normal    = primer partido del día − PREDICTION_LEAD_MINUTES
  con prórroga ON = primer partido del día (se extiende hasta el kickoff, nunca más)

Un partido es pronosticable si está SCHEDULED y `now` es anterior a ese límite.
"""
from datetime import datetime, timedelta, timezone, tzinfo
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.time import tz_day
from app.crud.app_state import app_state_crud
from app.crud.matches import match_crud
from app.models.match import Match, MatchStatus


def _limit(first_kickoff: datetime, override: bool) -> datetime:
    """Instante en que cierran los pronósticos de la jornada."""
    if override:
        return first_kickoff
    return first_kickoff - timedelta(minutes=settings.PREDICTION_LEAD_MINUTES)


def _predictable(match: Match, first_kickoff: datetime | None, override: bool, now: datetime) -> bool:
    if match.status != MatchStatus.SCHEDULED or first_kickoff is None:
        return False
    return now < _limit(first_kickoff, override)


async def annotate_predictable(db: AsyncSession, matches: list[Match], tz: tzinfo) -> None:
    """Setea `match.predictable` en cada partido (atributo transitorio que serializa
    MatchOut). Una lectura del interruptor + una de kickoffs para toda la lista."""
    if not matches:
        return
    override = await app_state_crud.get_prediction_override(db)
    first_kickoffs = await match_crud.day_first_kickoffs(db, tz)
    now = datetime.now(timezone.utc)
    for match in matches:
        fk = first_kickoffs.get(tz_day(match.match_date, tz))
        match.predictable = _predictable(match, fk, override, now)


async def ensure_predictable(db: AsyncSession, match: Match, tz: tzinfo) -> None:
    """Valida que el partido admita pronóstico ahora; si no, lanza 400 con el motivo.
    Autoridad final del POST (el flag del frontend es orientativo/cacheado)."""
    if match.status != MatchStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="No se puede predecir un partido en curso o finalizado.")

    first_kickoffs = await match_crud.day_first_kickoffs(db, tz)
    fk = first_kickoffs.get(tz_day(match.match_date, tz))
    if fk is None:  # sin fecha de jornada conocida: no debería ocurrir
        return

    now = datetime.now(timezone.utc)
    if now >= fk:
        raise HTTPException(status_code=400, detail="El primer partido de la jornada ya comenzó: no se puede predecir.")

    override = await app_state_crud.get_prediction_override(db)
    if now >= _limit(fk, override):
        raise HTTPException(status_code=400, detail="El plazo para enviar pronósticos de esta jornada ya cerró.")
