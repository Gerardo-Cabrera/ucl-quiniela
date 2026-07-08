import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { matchesApi, predictionsApi, leaderboardApi, top8Api, configApi, statsApi, matchdaysApi } from "@/api";
import type { MatchPhase, MatchStatus } from "@/types";

// ── CONFIG ────────────────────────────────────────────────────────────────────

export const useTeamsConfig = () =>
  useQuery({
    queryKey: ["config", "teams"],
    queryFn:  configApi.getTeams,
    staleTime: Infinity,
  });

// ── MATCHES ───────────────────────────────────────────────────────────────────

export const useMatches = (filters?: { phase?: MatchPhase; status?: MatchStatus }) =>
  useQuery({
    queryKey: ["matches", filters],
    queryFn:  () => matchesApi.getAll(filters),
    refetchInterval: 60_000, // refresca cada minuto
  });

export const useMatchPlayers = (matchId: number) =>
  useQuery({
    queryKey: ["matches", matchId, "players"],
    queryFn:  () => matchesApi.getPlayers(matchId),
    enabled:  !!matchId,
    staleTime: 1000 * 60 * 60, // las plantillas casi no cambian: cachear 1 h
  });

// ── PREDICTIONS ───────────────────────────────────────────────────────────────

export const useMyPredictions = () =>
  useQuery({
    queryKey: ["predictions", "mine"],
    queryFn:  predictionsApi.getMine,
  });

export const useSavePrediction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.save,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["predictions"] });
    },
  });
};

export const useDeletePrediction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["predictions"] });
    },
  });
};

// Interruptor admin de prórroga de pronósticos (solo se consulta si es admin).
export const usePredictionOverride = (enabled: boolean) =>
  useQuery({
    queryKey: ["predictions", "override"],
    queryFn:  predictionsApi.getOverride,
    enabled,
  });

export const useSetPredictionOverride = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.setOverride,
    onSuccess: () => {
      // Cambió la ventana: refresca partidos (predictable) y el propio estado.
      qc.invalidateQueries({ queryKey: ["predictions", "override"] });
      qc.invalidateQueries({ queryKey: ["matches"] });
    },
  });
};

// ── LEADERBOARD ───────────────────────────────────────────────────────────────

export const useLeaderboard = () =>
  useQuery({
    queryKey: ["leaderboard"],
    queryFn:  leaderboardApi.get,
    refetchInterval: 60_000, // refresca cada minuto (los puntos cambian cada 30 min en backend)
  });

// ── STATS / MATCHDAYS ───────────────────────────────────────────────────────────

export const useStats = () =>
  useQuery({
    queryKey: ["stats"],
    queryFn:  statsApi.get,
    refetchInterval: 60_000,
  });

export const useMatchdays = () =>
  useQuery({
    queryKey: ["matchdays"],
    queryFn:  matchdaysApi.get,
    refetchInterval: 60_000,
  });

// ── TOP 8 ─────────────────────────────────────────────────────────────────────

export const useMyTop8 = () =>
  useQuery({
    queryKey: ["top8", "mine"],
    queryFn:  top8Api.getMine,
  });

export const useSaveTop8 = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: top8Api.save,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["top8"] });
    },
  });
};
