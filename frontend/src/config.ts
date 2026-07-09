/**
 * Constantes centralizadas del frontend.
 * Cambiar aquí en lugar de hardcodear en múltiples archivos.
 */

export const AUTH_STORAGE_KEY = "ucl-auth";

// Cierre de sesión por inactividad: se cierra tras 1 h sin interacción del usuario.
export const LAST_ACTIVITY_KEY = "ucl-last-activity";
export const SESSION_IDLE_MS = 60 * 60 * 1000;

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export const TOASTER_STYLE = {
  background: "#1a1f3d",
  color: "#c9c9d1",
  border: "1px solid rgba(255,255,255,0.1)",
} as const;
