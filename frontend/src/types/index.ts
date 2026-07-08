// ── ENUMS ─────────────────────────────────────────────────────────────────────

export type MatchPhase =
  | "league"
  | "knockout_playoffs"
  | "round_of_16"
  | "quarter_finals"
  | "semi_finals"
  | "final";

export type MatchStatus = "scheduled" | "live" | "finished" | "postponed";

// ── MODELS ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  team_name: string;
  alias: string | null;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export interface Match {
  id: number;
  api_fixture_id: number;
  home_team: string;
  away_team: string;
  home_team_logo: string | null;
  away_team_logo: string | null;
  home_score: number | null;
  away_score: number | null;
  penalty_home: number | null;
  penalty_away: number | null;
  elapsed: number | null;
  first_goal_team: string | null;
  first_goal_player: string | null;
  phase: MatchPhase;
  status: MatchStatus;
  match_date: string;
  predictable: boolean;   // ¿se puede pronosticar ahora? (lo decide el backend)
}

export interface PredictionOverride {
  enabled: boolean;       // interruptor de prórroga de pronósticos (admin)
  lead_minutes: number;   // plazo normal: minutos antes del 1er partido del día
}

export interface Player {
  api_player_id: number;
  name: string;
  team_name: string;
  position: string | null;
}

export interface Prediction {
  id: number;
  match_id: number;
  predicted_home: number;
  predicted_away: number;
  first_goal_player_id: number | null;
  first_goal_player: string | null;
  points_earned: number;
  is_calculated: boolean;
  match: Match;
}

export interface Top8Pick {
  id: number;
  position: number;
  team_name: string;
  points_earned: number;
  is_calculated: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  team_name: string;
  total_points: number;
  match_points: number;
  top8_points: number;
  predictions_count: number;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

// Las etiquetas de fase y estado se traducen con i18n
// (claves `phase.*` y `status.*` en locales/es.json).

// ── STATS (Aciertos) ────────────────────────────────────────────────────────────

export interface UserCount {
  team_name: string;
  count: number;
}

export interface FirstGoalMatch {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  scorer: string | null;
  hitters: string[];       // solo partidos con acierto (≥1)
}

export interface ExactMatch {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  score: string;           // marcador real, "2-1"
  hitters: string[];       // solo partidos con acierto (≥1)
}

export interface ScoreCount {
  score: string;
  count: number;
}

export interface StatsSummary {
  first_goal_matches: FirstGoalMatch[];
  first_goal_ranking: UserCount[];
  top_scores: ScoreCount[];
  exact_matches: ExactMatch[];
  exact_ranking: UserCount[];
}

// ── MATCHDAYS (MVPs) ────────────────────────────────────────────────────────────

export interface MatchdayUserPoints {
  user_id: number;
  team_name: string;
  points: number;
}

export interface MatchdayEntry {
  date: string;
  entries: MatchdayUserPoints[];
  mvp_points: number;
  mvps: string[];
}

export interface MvpRankEntry {
  team_name: string;
  count: number;
}

export interface MatchdaysSummary {
  days: MatchdayEntry[];
  mvp_ranking: MvpRankEntry[];
}

