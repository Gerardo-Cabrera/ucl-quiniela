/** Extrae un mensaje legible del error de axios. `detail` es string en nuestras
 *  HTTPException; en un 422 de Pydantic es una lista {msg, loc} (se toma el primero,
 *  quitando el prefijo "Value error, " de los validadores propios). */
export function apiErrorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return (detail[0]?.msg ?? "").replace(/^Value error, /, "") || fallback;
  }
  return fallback;
}
