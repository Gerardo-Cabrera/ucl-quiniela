import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import type { Match } from "@/types";

/** Probabilidad de victoria pre-partido (local · empate · visitante) del próximo
 *  partido de cada equipo, según API-Football. Solo se pinta si el backend ya la
 *  sincronizó y MIENTRAS el pronóstico del partido siga abierto (`predictable`: la
 *  misma regla del backend que habilita "Pronosticar", plazo de la jornada + prórroga).
 *  Cerrado el plazo ya no se puede usar para decidir nada, así que se oculta.
 *  `placeholder`: conservar el hueco (invisible) aunque no haya nada que mostrar, para
 *  que las tarjetas de una misma fila mantengan el pie al mismo nivel. */
export function WinProbabilityBar({ match, placeholder = false }: { match: Match; placeholder?: boolean }) {
  const { t } = useTranslation();
  const { prob_home: home, prob_draw: draw, prob_away: away, prob_updated_at: updated } = match;
  const visible = home != null && draw != null && away != null && match.predictable;
  if (!visible && !placeholder) return null;

  const title = t("probability.title", {
    date: updated ? format(new Date(updated), "d MMM HH:mm", { locale: es }) : t("common.dash"),
  });
  return (
    <div
      className={clsx("-mt-1 mb-4", !visible && "invisible")}
      title={visible ? title : undefined}
      aria-label={visible ? title : undefined}
      aria-hidden={!visible}
    >
      <div className="flex h-1.5 rounded-full overflow-hidden bg-ucl-navy/60">
        <div className="bg-ucl-gold"      style={{ width: `${home ?? 0}%` }} />
        <div className="bg-ucl-silver/50" style={{ width: `${draw ?? 0}%` }} />
        <div className="bg-blue-400"      style={{ width: `${away ?? 0}%` }} />
      </div>
      {/* Una etiqueta por tramo, alineada con su equipo: "Victoria" a cada lado (local a
          la izquierda, visitante a la derecha, con el color de su tramo) y "Empate" en
          el centro, para que la barra se entienda sin tooltip. */}
      <div className="flex items-center justify-between gap-2 mt-1 text-[11px] font-mono">
        <span className="text-ucl-gold">{t("probability.win")} {home ?? 0}%</span>
        <span className="text-ucl-silver/60">{t("probability.draw")} {draw ?? 0}%</span>
        <span className="text-blue-300">{t("probability.win")} {away ?? 0}%</span>
      </div>
    </div>
  );
}
