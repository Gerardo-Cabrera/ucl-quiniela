"""Sanciones por tarjetas, deducidas de las tarjetas guardadas por partido
(`Match.card_events`). Regla pura, sin BD ni red.

Por qué hace falta: API-Football (`/injuries`) informa de quien se pierde un partido por
ROJA, pero no de quien cumple ciclo de amarillas, y si el partido aún no tiene parte de
bajas no informa de nadie. Comprobado en la jornada 5 de 2026/27: de los seis sancionados
que salen de aplicar el reglamento, la API daba tres (los tres por roja).

Reglamento de la UEFA Champions League (tarjetas, desde la fase de liga):
- **Expulsión** → sanción en el siguiente partido del equipo en la competición.
- **Tercera amonestación** y cada impar posterior (5.ª, 7.ª...) → sanción en el
  siguiente partido.
- **Dos amarillas en el mismo partido** son una expulsión, y esas dos no cuentan para
  el ciclo. Una amarilla seguida de roja directa sí cuenta.
- Las amarillas **caducan al terminar los cuartos de final**: semifinales y final
  cuentan de cero. La sanción ya ganada en cuartos se cumple igualmente.

Lo que NO se puede saber desde aquí: sanciones de más de un partido (las decide el comité
disciplinario) y tarjetas retiradas tras un recurso. Las primeras suelen llegar por la
API como baja; por eso este cálculo se SUMA a las bajas de la API, no las sustituye.
"""
from collections import Counter
from collections.abc import Sequence
from typing import Any

from app.models.match import MatchPhase, MatchStatus

# Motivos, en el vocabulario de API-Football (el mismo que traen sus bajas).
RED_CARD = "Red Card"
YELLOW_CARDS = "Yellow Cards"

# Fases que cuentan las amarillas de cero (ver arriba).
_AFTER_QUARTER_FINALS = {MatchPhase.SEMI_FINALS, MatchPhase.FINAL}


def suspended_for_match(team: str, match_id: int, schedule: Sequence[Any]) -> dict[int, str]:
    """Jugadores de `team` sancionados para el partido `match_id`: `api_player_id` →
    motivo (`RED_CARD` o `YELLOW_CARDS`).

    `schedule`: TODOS los partidos de `team` en orden cronológico, del estado que sea,
    cada uno con `id`, `phase`, `status` y `card_events`. La sanción se cumple en el
    partido SIGUIENTE al de la tarjeta, así que solo se puede afirmar algo si el partido
    inmediatamente anterior (sin contar los aplazados) ya terminó y tiene sus tarjetas
    guardadas; si no (p. ej. se consulta un partido de dentro de dos jornadas) no se
    marca a nadie."""
    # Un partido aplazado no se jugó: la sanción se cumple en el siguiente que sí se
    # juegue, así que no cuenta como "el anterior" (el propio partido consultado se
    # conserva aunque esté aplazado, para poder situarlo en el calendario).
    schedule = [m for m in schedule if m.status != MatchStatus.POSTPONED or m.id == match_id]
    index = next((i for i, m in enumerate(schedule) if m.id == match_id), 0)
    if index == 0:
        return {}
    previous = schedule[index - 1]
    if previous.status != MatchStatus.FINISHED or previous.card_events is None:
        return {}

    fresh_start = previous.phase in _AFTER_QUARTER_FINALS
    cautions: Counter[int] = Counter()      # amonestaciones que cuentan para el ciclo
    suspended: dict[int, str] = {}
    for played in schedule[:index]:
        if played.status != MatchStatus.FINISHED or (played.phase in _AFTER_QUARTER_FINALS) != fresh_start:
            continue
        yellows: Counter[int] = Counter()
        sent_off: set[int] = set()          # roja directa
        double: set[int] = set()            # expulsado por doble amarilla
        for card in played.card_events or []:
            player_id = card.get("player_id")
            if player_id is None or card.get("team") != team:
                continue
            kind = card.get("card")
            if kind == "yellow":
                yellows[player_id] += 1
            elif kind == "second_yellow":
                double.add(player_id)
            else:
                sent_off.add(player_id)
        double.update(pid for pid, n in yellows.items() if n >= 2)
        counted = [pid for pid in yellows if pid not in double]
        cautions.update(counted)
        if played is previous:
            for player_id in counted:
                if cautions[player_id] >= 3 and cautions[player_id] % 2 == 1:
                    suspended[player_id] = YELLOW_CARDS
            # Una expulsión pesa más que el ciclo: se anota al final.
            suspended.update(dict.fromkeys(sent_off | double, RED_CARD))
    return suspended
