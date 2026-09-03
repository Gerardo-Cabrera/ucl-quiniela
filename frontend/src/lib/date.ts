import { format } from "date-fns";
import { es } from "date-fns/locale";

/** Convierte un día ISO "YYYY-MM-DD" a Date al mediodía local: evita que el cambio
 *  de zona horaria reste un día al formatear (fuente única para Jornada y MVPs). */
export function isoDayToDate(day: string): Date {
  return new Date(day + "T12:00:00");
}

export interface DayGroup<T> {
  day: string;    // "yyyy-MM-dd" local
  date: Date;     // fecha del primer elemento del día (para la cabecera)
  items: T[];
}

/** Agrupa por día local y ordena días y elementos por fecha en el sentido pedido
 *  (`asc`: Partidos, cronológico; `desc`: Mis Pronósticos, lo más reciente primero).
 *  Empates de hora conservan el orden de llegada (sort estable). Cabeceras de fecha
 *  en Partidos y Mis Pronósticos. */
export function groupByDay<T>(
  items: T[],
  getDate: (item: T) => string,
  order: "asc" | "desc" = "asc",
): DayGroup<T>[] {
  const sign = order === "asc" ? 1 : -1;
  const groups = new Map<string, DayGroup<T>>();
  for (const item of items) {
    const date = new Date(getDate(item));
    const day = format(date, "yyyy-MM-dd");
    const group = groups.get(day) ?? { day, date, items: [] };
    group.items.push(item);
    groups.set(day, group);
  }
  for (const group of groups.values()) {
    group.items.sort((a, b) => sign * (Date.parse(getDate(a)) - Date.parse(getDate(b))));
  }
  return [...groups.values()].sort((a, b) => sign * a.day.localeCompare(b.day));
}

/** "Lunes 8 de septiembre" (inicial en mayúscula; date-fns la da en minúscula). */
export function formatDayHeading(date: Date): string {
  const text = format(date, "EEEE d 'de' MMMM", { locale: es });
  return text.charAt(0).toUpperCase() + text.slice(1);
}
