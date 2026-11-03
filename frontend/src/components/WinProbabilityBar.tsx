import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import type { Match } from "@/types";

/** Probabilidad de victoria pre-partido (local · empate · visitante) del próximo
 *  partido de cada equipo, según API-Football. Solo se pinta si el backend ya la
 *  sincronizó y MIENTRAS el pronóstico del partido siga abierto (`predictable`: la
 *  misma regla del backend que habilita "Pronosticar", plazo de la jornada + prórroga).
 *  Cerrado el plazo ya no se puede usar para decidir nada, así que se oculta. */
export function WinProbabilityBar({ match }: { match: Match }) {
  const { t } = useTranslation();
  const { prob_home: home, prob_draw: draw, prob_away: away, prob_updated_at: updated } = match;
  if (home == null || draw == null || away == null || !match.predictable) return null;

  const title = t("probability.title", {
    date: updated ? format(new Date(updated), "d MMM HH:mm", { locale: es }) : t("common.dash"),
  });
  return (
    <div className="-mt-1 mb-4" title={title} aria-label={title}>
      <div className="flex h-1.5 rounded-full overflow-hidden bg-ucl-navy/60">
        <div className="bg-ucl-gold"      style={{ width: `${home}%` }} />
        <div className="bg-ucl-silver/50" style={{ width: `${draw}%` }} />
        <div className="bg-blue-400"      style={{ width: `${away}%` }} />
      </div>
      <div className="flex items-center justify-between mt-1 text-[11px] font-mono">
        <span className="text-ucl-gold">{home}%</span>
        <span className="text-ucl-silver/60">{t("probability.label")} · {t("probability.draw")} {draw}%</span>
        <span className="text-blue-300">{away}%</span>
      </div>
    </div>
  );
}
