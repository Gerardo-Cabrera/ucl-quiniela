"""
Unit tests para el motor de puntuación UCL Quiniela.
Cubre: resultado exacto, victoria/empate, primer gol, fases liga vs knockout, Top 8.
"""
import pytest
from app.models.match import MatchPhase
from app.services.scoring import (
    calculate_match_points,
    calculate_top8_points,
    LEAGUE_POINTS,
    KNOCKOUT_POINTS,
    TOP8_POINTS,
    _get_outcome,
)


# ── HELPERS ───────────────────────────────────────────────────────────────────


class TestGetOutcome:
    def test_home_win(self):
        assert _get_outcome(3, 1) == "home"

    def test_away_win(self):
        assert _get_outcome(0, 2) == "away"

    def test_draw(self):
        assert _get_outcome(1, 1) == "draw"

    def test_draw_zero(self):
        assert _get_outcome(0, 0) == "draw"


# ── LEAGUE PHASE SCORING ────────────────────────────────────────────────────


class TestLeagueScoring:
    """Tests para la fase de liga (league)."""

    def _calc(self, **kwargs):
        defaults = {
            "predicted_home": 0,
            "predicted_away": 0,
            "predicted_first_goal_player_id": None,
            "actual_home": 0,
            "actual_away": 0,
            "actual_first_goal_player_id": None,
            "phase": MatchPhase.LEAGUE,
        }
        defaults.update(kwargs)
        return calculate_match_points(**defaults)

    def test_exact_score(self):
        """Resultado exacto: 8 pts en liga."""
        r = self._calc(
            predicted_home=2, predicted_away=1,
            actual_home=2, actual_away=1,
        )
        assert r["exact"] == LEAGUE_POINTS["exact"]
        assert r["outcome"] == 0
        assert r["total"] == LEAGUE_POINTS["exact"]

    def test_exact_draw(self):
        """Empate exacto: 8 pts (no 6 de empate)."""
        r = self._calc(
            predicted_home=1, predicted_away=1,
            actual_home=1, actual_away=1,
        )
        assert r["exact"] == LEAGUE_POINTS["exact"]
        assert r["outcome"] == 0
        assert r["total"] == LEAGUE_POINTS["exact"]

    def test_correct_winner_wrong_score(self):
        """Acierta ganador, falla marcador: 5 pts."""
        r = self._calc(
            predicted_home=3, predicted_away=0,
            actual_home=2, actual_away=1,
        )
        assert r["exact"] == 0
        assert r["outcome"] == LEAGUE_POINTS["win"]
        assert r["total"] == LEAGUE_POINTS["win"]

    def test_correct_draw_wrong_score(self):
        """Acierta empate, falla marcador: 6 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=2,
            actual_home=0, actual_away=0,
        )
        assert r["exact"] == 0
        assert r["outcome"] == LEAGUE_POINTS["draw"]
        assert r["total"] == LEAGUE_POINTS["draw"]

    def test_wrong_outcome(self):
        """Falla resultado completamente: 0 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            actual_home=0, actual_away=3,
        )
        assert r["total"] == 0

    def test_first_goal_correct(self):
        """Primer goleador correcto (mismo id): +3 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            predicted_first_goal_player_id=10,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == LEAGUE_POINTS["first_goal"]
        assert r["total"] == LEAGUE_POINTS["win"] + LEAGUE_POINTS["first_goal"]

    def test_first_goal_wrong(self):
        """Primer goleador incorrecto (id distinto): 0 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            predicted_first_goal_player_id=20,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == 0

    def test_first_goal_case_insensitive(self):
        """Mismo jugador (mismo id): otorga puntos."""
        r = self._calc(
            predicted_home=1, predicted_away=0,
            predicted_first_goal_player_id=10,
            actual_home=1, actual_away=0,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == LEAGUE_POINTS["first_goal"]

    def test_first_goal_none_predicted(self):
        """Sin predicción de primer gol: no suma."""
        r = self._calc(
            predicted_home=1, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=0,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == 0

    def test_first_goal_none_actual(self):
        """Sin primer gol real (e.g. 0-0): no suma."""
        r = self._calc(
            predicted_home=0, predicted_away=0,
            predicted_first_goal_player_id=20,
            actual_home=0, actual_away=0,
            actual_first_goal_player_id=None,
        )
        assert r["first_goal"] == 0

    def test_exact_plus_first_goal(self):
        """Resultado exacto + primer gol = max pts en liga."""
        r = self._calc(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=33,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=33,
        )
        assert r["total"] == LEAGUE_POINTS["exact"] + LEAGUE_POINTS["first_goal"]

    def test_exact_and_outcome_mutually_exclusive(self):
        """Exacto y victoria/empate son mutuamente excluyentes."""
        r = self._calc(
            predicted_home=3, predicted_away=1,
            actual_home=3, actual_away=1,
        )
        assert r["exact"] == LEAGUE_POINTS["exact"]
        assert r["outcome"] == 0


# ── KNOCKOUT PHASE SCORING ───────────────────────────────────────────────────


class TestKnockoutScoring:
    """Tests para fases eliminatorias (knockout)."""

    @pytest.mark.parametrize("phase", [
        MatchPhase.KNOCKOUT_PLAYOFFS,
        MatchPhase.ROUND_OF_16,
        MatchPhase.QUARTER_FINALS,
        MatchPhase.SEMI_FINALS,
        MatchPhase.FINAL,
    ])
    def test_exact_score_knockout(self, phase):
        r = calculate_match_points(
            predicted_home=1, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=0,
            actual_first_goal_player_id=None,
            phase=phase,
        )
        assert r["exact"] == KNOCKOUT_POINTS["exact"]
        assert r["total"] == KNOCKOUT_POINTS["exact"]

    def test_correct_winner_knockout(self):
        r = calculate_match_points(
            predicted_home=3, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=None,
            phase=MatchPhase.FINAL,
        )
        assert r["outcome"] == KNOCKOUT_POINTS["win"]

    def test_correct_draw_knockout(self):
        r = calculate_match_points(
            predicted_home=2, predicted_away=2,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=1,
            actual_first_goal_player_id=None,
            phase=MatchPhase.QUARTER_FINALS,
        )
        assert r["outcome"] == KNOCKOUT_POINTS["draw"]

    def test_first_goal_knockout(self):
        r = calculate_match_points(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=33,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=33,
            phase=MatchPhase.SEMI_FINALS,
        )
        assert r["first_goal"] == KNOCKOUT_POINTS["first_goal"]
        assert r["total"] == KNOCKOUT_POINTS["exact"] + KNOCKOUT_POINTS["first_goal"]

    def test_max_knockout_points(self):
        """Max en final: exacto 11 + primer gol 5 = 16."""
        r = calculate_match_points(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=44,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=44,
            phase=MatchPhase.FINAL,
        )
        assert r["total"] == KNOCKOUT_POINTS["exact"] + KNOCKOUT_POINTS["first_goal"]
        assert r["total"] == 16


# ── TOP 8 SCORING ────────────────────────────────────────────────────────────


class TestTop8Scoring:
    ACTUAL_TOP8 = [
        "Real Madrid", "Manchester City", "Bayern Munich", "Barcelona",
        "Arsenal", "Liverpool", "Inter Milan", "PSG",
    ]

    def test_perfect_pick(self):
        """Equipo correcto en posición correcta: 5 pts."""
        picks = [{"position": 1, "team_name": "Real Madrid"}]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["points_earned"] == TOP8_POINTS["team_and_pos"]

    def test_team_correct_wrong_position(self):
        """Equipo correcto, posición incorrecta: 3 pts."""
        picks = [{"position": 3, "team_name": "Real Madrid"}]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["points_earned"] == TOP8_POINTS["team_only"]

    def test_team_not_in_top8(self):
        """Equipo no está en el top 8 real: 0 pts."""
        picks = [{"position": 1, "team_name": "Celtic"}]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["points_earned"] == 0

    def test_case_insensitive(self):
        """Comparación case-insensitive."""
        picks = [{"position": 1, "team_name": "real madrid"}]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["points_earned"] == TOP8_POINTS["team_and_pos"]

    def test_full_8_picks(self):
        """8 picks perfectos = 40 pts."""
        picks = [
            {"position": i + 1, "team_name": team}
            for i, team in enumerate(self.ACTUAL_TOP8)
        ]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        total = sum(r["points_earned"] for r in results)
        assert total == TOP8_POINTS["team_and_pos"] * 8
        assert total == 40

    def test_all_wrong_teams(self):
        """Ningún equipo correcto = 0 pts."""
        picks = [
            {"position": i + 1, "team_name": f"FakeTeam{i}"}
            for i in range(8)
        ]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        total = sum(r["points_earned"] for r in results)
        assert total == 0

    def test_mixed_results(self):
        """Mezcla: posición exacta + solo equipo + miss."""
        picks = [
            {"position": 1, "team_name": "Real Madrid"},       # exact pos → 5
            {"position": 2, "team_name": "Barcelona"},          # wrong pos (actual pos 4) → 3
            {"position": 3, "team_name": "Nottingham Forest"},  # not in top8 → 0
        ]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["points_earned"] == 5
        assert results[1]["points_earned"] == 3
        assert results[2]["points_earned"] == 0

    def test_preserves_original_names(self):
        """Retorna los nombres originales, no lowercased."""
        picks = [{"position": 1, "team_name": "Real Madrid"}]
        results = calculate_top8_points(picks, self.ACTUAL_TOP8)
        assert results[0]["team_name"] == "Real Madrid"

    def test_empty_picks(self):
        """Sin picks = lista vacía."""
        results = calculate_top8_points([], self.ACTUAL_TOP8)
        assert results == []
