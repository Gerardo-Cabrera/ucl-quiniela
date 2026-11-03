import i18n from "@/i18n";

/** Extrae un mensaje legible del error de axios.
 *  - 429 (rate limit): slowapi responde `{"error": ...}` sin `detail`, así que antes
 *    caía en el genérico; se traduce a un mensaje claro ("espera un minuto").
 *  - Sin respuesta (red caída, backend dormido tras agotar los reintentos): mensaje
 *    de conexión, no "ocurrió un error".
 *  - `detail` es string en nuestras HTTPException; en un 422 de Pydantic es una lista
 *    {msg, loc} (se toma el primero, quitando el prefijo "Value error, "). */
export function apiErrorMessage(err: any, fallback: string): string {
  const status = err?.response?.status;
  if (status === 429) return i18n.t("common.tooManyRequests");
  if (err?.isAxiosError && !err.response) return i18n.t("common.networkError");
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return (detail[0]?.msg ?? "").replace(/^Value error, /, "") || fallback;
  }
  return fallback;
}
