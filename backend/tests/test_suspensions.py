"""Sanciones por tarjetas deducidas del reglamento (services/suspensions.py): regla pura
sobre el calendario de un equipo. Cada partido es (fase, estado, tarjetas) y siempre se
pregunta por el ÚLTIMO de la lista."""
from types import SimpleNamespace

from app.models.match import MatchPhase, MatchStatus
from app.services.suspensions import RED_CARD, YELLOW_CARDS, suspended_for_match

TEAM = "Real Madrid"
P = 10          # el jugador que se sigue
OTHER = 11

LEAGUE, QUARTERS, SEMIS, FINAL = (
    MatchPhase.LEAGUE, MatchPhase.QUARTER_FINALS, MatchPhase.SEMI_FINALS, MatchPhase.FINAL,
)


def card(kind: str = "yellow", player_id: int = P, team: str = TEAM) -> dict:
    return {"player_id": player_id, "player": "x", "team": team, "card": kind}


def played(*cards: dict, phase: MatchPhase = LEAGUE) -> tuple:
    return phase, MatchStatus.FINISHED, list(cards)


def upcoming(phase: MatchPhase = LEAGUE) -> tuple:
    return phase, MatchStatus.SCHEDULED, None


def suspended(*matches: tuple) -> dict[int, str]:
    schedule = [
        SimpleNamespace(id=i, phase=phase, status=status, card_events=cards)
        for i, (phase, status, cards) in enumerate(matches, start=1)
    ]
    return suspended_for_match(TEAM, schedule[-1].id, schedule)


def test_third_yellow_suspends_for_the_next_match():
    assert suspended(played(card()), played(card()), played(card()), upcoming()) == {P: YELLOW_CARDS}


def test_two_yellows_do_not_suspend():
    assert suspended(played(card()), played(card()), upcoming()) == {}


def test_suspension_is_served_once():
    """La 3.ª amarilla fue hace dos partidos: la sanción ya se cumplió en el anterior."""
    assert suspended(played(card()), played(card()), played(card()), played(), upcoming()) == {}


def test_fourth_yellow_does_not_suspend_but_the_fifth_does():
    four = [played(card())] * 3 + [played(), played(card())]
    assert suspended(*four, upcoming()) == {}
    assert suspended(*four, played(card()), upcoming()) == {P: YELLOW_CARDS}


def test_straight_red_suspends():
    assert suspended(played(card("red")), upcoming()) == {P: RED_CARD}


def test_two_yellows_in_one_match_are_a_dismissal_and_do_not_count_for_the_cycle():
    assert suspended(played(card(), card()), upcoming()) == {P: RED_CARD}
    assert suspended(played(card(), card("second_yellow")), upcoming()) == {P: RED_CARD}
    # Amarilla, expulsión por doble amarilla (no cuenta), amarilla: lleva DOS, no tres.
    assert suspended(played(card()), played(card(), card()), played(card()), upcoming()) == {}


def test_yellow_before_a_straight_red_still_counts():
    """Amarilla y roja directa en el mismo partido: sancionado por la roja, y esa amarilla
    es la tercera del ciclo (la cuarta ya no sanciona, la quinta sí)."""
    history = [played(card()), played(card()), played(card(), card("red"))]
    assert suspended(*history, upcoming()) == {P: RED_CARD}
    assert suspended(*history, played(), played(card()), upcoming()) == {}
    assert suspended(*history, played(), played(card()), played(card()), upcoming()) == {P: YELLOW_CARDS}


def test_nothing_is_claimed_until_the_previous_match_is_played_and_has_its_cards():
    three = [played(card())] * 3
    # El partido consultado no es el siguiente: hay otro por jugar en medio.
    assert suspended(*three, upcoming(), upcoming()) == {}
    # El anterior terminó pero aún no tiene sus tarjetas guardadas.
    assert suspended(*three[:2], (LEAGUE, MatchStatus.FINISHED, None), upcoming()) == {}
    # Primer partido del equipo, o partido que no está en su calendario.
    assert suspended(upcoming()) == {}
    assert suspended_for_match(TEAM, 99, []) == {}


def test_a_postponed_match_does_not_serve_the_suspension():
    """El partido siguiente al de la tarjeta se aplazó: la sanción se cumple en el primero
    que sí se juegue. Un aplazado tampoco tapa una sanción ya cumplida."""
    postponed = (LEAGUE, MatchStatus.POSTPONED, None)
    three = [played(card())] * 3
    assert suspended(*three, postponed, upcoming()) == {P: YELLOW_CARDS}
    assert suspended(played(card("red")), postponed, postponed, upcoming()) == {P: RED_CARD}
    assert suspended(*three, played(), postponed, upcoming()) == {}        # ya la cumplió
    # Si el partido consultado es el aplazado, se evalúa como cualquier otro.
    assert suspended(*three, postponed) == {P: YELLOW_CARDS}


def test_only_the_teams_own_cards_count():
    rival = card(player_id=OTHER, team="Barcelona")
    assert suspended(played(rival), played(rival), played(rival, card("red", OTHER, "Barcelona")), upcoming()) == {}


def test_yellows_expire_after_the_quarter_finals_but_the_pending_ban_is_served():
    # 3.ª amarilla en cuartos: se cumple en la ida de semifinales.
    assert suspended(played(card()), played(card()), played(card(), phase=QUARTERS), upcoming(SEMIS)) == {P: YELLOW_CARDS}
    # Con cuatro de antes, una amarilla en la ida de semifinales es la PRIMERA del ciclo nuevo.
    four = [played(card())] * 4
    assert suspended(*four, played(card(), phase=SEMIS), upcoming(SEMIS)) == {}
    # La roja en semifinales sí deja sin final.
    assert suspended(*four, played(card("red"), phase=SEMIS), upcoming(FINAL)) == {P: RED_CARD}


def test_several_players_in_the_same_match():
    assert suspended(
        played(card(), card(player_id=OTHER)), played(card()),
        played(card(), card("red", OTHER)), upcoming(),
    ) == {P: YELLOW_CARDS, OTHER: RED_CARD}
