import apiClient from "@/api/client";
import type {
  Match, Prediction, PredictionOverride, LeaderboardEntry, Top8Pick, Player,
  TournamentPick, TournamentStats, StatsSummary, MatchdaysSummary,
  MatchPhase, MatchStatus,
} from "@/types";

// ── MATCHES ───────────────────────────────────────────────────────────────────

export const matchesApi = {
  getAll: async (params?: { phase?: MatchPhase; status?: MatchStatus }): Promise<Match[]> => {
    const { data } = await apiClient.get("/api/matches", { params });
    return data;
  },
  getPlayers: async (id: number): Promise<Player[]> => {
    const { data } = await apiClient.get(`/api/matches/${id}/players`);
    return data;
  },
};

// ── PREDICTIONS ───────────────────────────────────────────────────────────────

export const predictionsApi = {
  getMine: async (): Promise<Prediction[]> => {
    const { data } = await apiClient.get("/api/predictions");
    return data;
  },
  getForUser: async (userId: number): Promise<Prediction[]> => {
    const { data } = await apiClient.get(`/api/predictions/user/${userId}`);
    return data;
  },
  save: async (payload: {
    match_id: number;
    predicted_home: number;
    predicted_away: number;
    first_goal_player_id?: number;
  }): Promise<Prediction> => {
    const { data } = await apiClient.post("/api/predictions", payload);
    return data;
  },
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/predictions/${id}`);
  },
  getOverride: async (): Promise<PredictionOverride> => {
    const { data } = await apiClient.get("/api/predictions/override");
    return data;
  },
  setOverride: async (enabled: boolean): Promise<PredictionOverride> => {
    const { data } = await apiClient.put("/api/predictions/override", { enabled });
    return data;
  },
};

// ── LEADERBOARD ───────────────────────────────────────────────────────────────

export const leaderboardApi = {
  get: async (): Promise<LeaderboardEntry[]> => {
    const { data } = await apiClient.get("/api/leaderboard");
    return data;
  },
};

// ── STATS (Aciertos) ────────────────────────────────────────────────────────────

export const statsApi = {
  get: async (): Promise<StatsSummary> => {
    const { data } = await apiClient.get("/api/stats");
    return data;
  },
};

// ── MATCHDAYS (MVPs) ────────────────────────────────────────────────────────────

export const matchdaysApi = {
  get: async (): Promise<MatchdaysSummary> => {
    const { data } = await apiClient.get("/api/matchdays");
    return data;
  },
};

// ── CONFIG ────────────────────────────────────────────────────────────────────

export const configApi = {
  getTeams: async (): Promise<{ ucl_teams: string[] }> => {
    const { data } = await apiClient.get("/api/config/teams");
    return data;
  },
};

// ── TOP 8 ─────────────────────────────────────────────────────────────────────

export const top8Api = {
  getMine: async (): Promise<Top8Pick[]> => {
    const { data } = await apiClient.get("/api/top8/me");
    return data;
  },
  getForUser: async (userId: number): Promise<Top8Pick[]> => {
    const { data } = await apiClient.get(`/api/top8/user/${userId}`);
    return data;
  },
  getActual: async (): Promise<string[]> => {
    const { data } = await apiClient.get("/api/top8/actual");
    return data;
  },
  save: async (picks: { position: number; team_name: string }[]): Promise<Top8Pick[]> => {
    const { data } = await apiClient.post("/api/top8", { picks });
    return data;
  },
};

// ── TORNEO (MVP + máximo goleador) ──────────────────────────────────────────────

export const tournamentApi = {
  getMine: async (): Promise<TournamentPick | null> => {
    const { data } = await apiClient.get("/api/tournament/me");
    return data;
  },
  getForUser: async (userId: number): Promise<TournamentPick | null> => {
    const { data } = await apiClient.get(`/api/tournament/user/${userId}`);
    return data;
  },
  getPlayers: async (): Promise<Player[]> => {
    const { data } = await apiClient.get("/api/tournament/players");
    return data;
  },
  getStats: async (): Promise<TournamentStats> => {
    const { data } = await apiClient.get("/api/tournament/stats");
    return data;
  },
  save: async (payload: {
    mvp_player_id?: number | null;
    top_scorer_player_id?: number | null;
  }): Promise<TournamentPick> => {
    const { data } = await apiClient.post("/api/tournament", payload);
    return data;
  },
};
