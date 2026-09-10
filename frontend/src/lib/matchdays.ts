import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { isoDayToDate } from "@/lib/date";
import type { RoundEntry } from "@/types";

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
