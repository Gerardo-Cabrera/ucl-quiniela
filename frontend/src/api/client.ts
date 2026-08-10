import axios from "axios";
import { API_BASE_URL, AUTH_STORAGE_KEY } from "@/config";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

/**
 * Lee el token JWT desde el store persistido de Zustand.
 * Zustand persist guarda en localStorage bajo la key "ucl-auth".
 */
function getPersistedToken(): string | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.state?.token ?? null;
  } catch {
    return null;
  }
}

// Adjunta el token JWT en cada request
apiClient.interceptors.request.use((config) => {
  const token = getPersistedToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Reintenta fallos TRANSITORIOS (sin respuesta = red, o 5xx) en operaciones
// idempotentes (GET y login): cubre el "arranque en frío" de Render tras
// inactividad, donde el primer intento despierta el backend pero falla y el
// segundo ya funciona. No reintenta mutaciones (evita duplicados) ni 4xx
// (401/409/422 son errores reales, no transitorios).
const RETRY_DELAYS_MS = [2000, 5000];

// Redirige al login si el token expira (excepto en endpoints de auth,
// donde el 401 es parte del flujo normal: credenciales incorrectas).
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const cfg = err.config;
    const status = err.response?.status;

    const transient = !err.response || status >= 500;
    const method = (cfg?.method ?? "get").toLowerCase();
    const idempotent = method === "get" || cfg?.url?.includes("/auth/login");
    const attempt = cfg?._retryCount ?? 0;
    if (cfg && transient && idempotent && attempt < RETRY_DELAYS_MS.length) {
      cfg._retryCount = attempt + 1;
      await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
      return apiClient(cfg);
    }

    const isAuthRequest = cfg?.url?.includes("/api/auth/");
    if (status === 401 && !isAuthRequest) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default apiClient;
