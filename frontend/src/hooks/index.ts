import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { matchesApi, predictionsApi, leaderboardApi, top8Api, configApi, statsApi, matchdaysApi } from "@/api";
import { useAuthStore } from "@/store/authStore";
import { LAST_ACTIVITY_KEY, SESSION_IDLE_MS } from "@/config";
import type { MatchPhase, MatchStatus } from "@/types";

// ── SESIÓN ──────────────────────────────────────────────────────────────────

/** Cierra la sesión tras SESSION_IDLE_MS de inactividad. La marca de actividad se
 *  guarda en localStorage (throttled) y se comprueba con cada interacción, al
 *  volver a la pestaña y cada 30 s: así una pestaña ya vencida no revive. */
export const useInactivityLogout = () => {
  const { isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    if (!isAuthenticated) return;

    const bump = () => localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    const enforce = (): boolean => {
      const last = Number(localStorage.getItem(LAST_ACTIVITY_KEY) || Date.now());
      if (Date.now() - last < SESSION_IDLE_MS) return false;
      localStorage.removeItem(LAST_ACTIVITY_KEY);
      logout();
      navigate("/login");
      toast(t("auth.sessionExpired"), { icon: "🔒" });
      return true;
    };

    if (!localStorage.getItem(LAST_ACTIVITY_KEY)) bump();
    if (enforce()) return;

    // Throttle: registrar actividad como mucho cada 30 s (no en cada scroll/pointer).
    let lastBump = 0;
    const onActivity = () => {
      if (enforce()) return;
      const now = Date.now();
      if (now - lastBump > 30_000) { lastBump = now; bump(); }
    };
    const events = ["pointerdown", "keydown", "scroll", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    document.addEventListener("visibilitychange", onActivity);
    const id = window.setInterval(enforce, 30_000);

    return () => {
      clearInterval(id);
      events.forEach((e) => window.removeEventListener(e, onActivity));
      document.removeEventListener("visibilitychange", onActivity);
    };
  }, [isAuthenticated, logout, navigate, t]);
};

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

// Pronósticos de otro participante, revelados por jornada iniciada (backend).
// enabled solo cuando hay usuario seleccionado (modal abierto).
export const useUserPredictions = (userId: number | null) =>
  useQuery({
    queryKey: ["predictions", "user", userId],
    queryFn:  () => predictionsApi.getForUser(userId!),
    enabled:  userId != null,
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
