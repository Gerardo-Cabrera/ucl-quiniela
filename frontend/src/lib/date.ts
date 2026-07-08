/** Convierte un día ISO "YYYY-MM-DD" a Date al mediodía local: evita que el cambio
 *  de zona horaria reste un día al formatear (fuente única para Jornada y MVPs). */
export function isoDayToDate(day: string): Date {
  return new Date(day + "T12:00:00");
}
