import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { isoDayToDate } from "@/lib/date";
import type { PointsGroup, RoundEntry } from "@/types";

/** Vista de las páginas Jornada y MVPs: por día o por jornada completa. */
export type MatchdayView = "days" | "rounds";

/** Etiquetas de día y de jornada completa, y las opciones de la vista, compartidas
 *  por Jornada y MVPs. "Jornada N" en fase de liga; en eliminatorias, la fase. */
export function useMatchdayLabels() {
  const { t } = useTranslation();
  const short = (day: string) => format(isoDayToDate(day), "d MMM", { locale: es });
  return {
    viewOptions: [
      { value: "days" as const, label: t("jornada.byDay") },
      { value: "rounds" as const, label: t("jornada.byRound") },
    ],
    dayTitle: (day: string) => format(isoDayToDate(day), "EEEE d 'de' MMMM", { locale: es }),
    dayShort: short,
    roundTitle: (r: RoundEntry) =>
      r.round_number != null ? t("jornada.round", { n: r.round_number }) : t(`phase.${r.phase}`),
    roundDates: (r: RoundEntry) => (r.start === r.end ? short(r.start) : `${short(r.start)} – ${short(r.end)}`),
  };
}

/** Ranking de MVPs: veces que cada equipo fue MVP en los grupos dados (desc,
 *  desempate alfabético). Filas para RankingCard. */
export function mvpRanking(groups: PointsGroup[]): { name: string; value: number }[] {
  const counts = new Map<string, number>();
  for (const g of groups) for (const name of g.mvps) counts.set(name, (counts.get(name) ?? 0) + 1);
  return [...counts]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name));
}
