import { useTranslation } from "react-i18next";
import type { Match, Prediction } from "@/types";

interface Props {
  prediction: Prediction;
  match: Match;
  /** Modo compacto (tarjeta de Partidos): sin etiquetas visibles, con tooltip
   *  "Primer gol" en el balón, y sin el real, que esa tarjeta ya muestra en su
   *  propia fila para todos. */
  compact?: boolean;
}

/** Línea de primer gol de una tarjeta de pronóstico:
 *  "⚽ Primer gol: elegido · Primer gol real: X ✓ +N" (compacta: "⚽ elegido ✓ +N").
 *  El elegido va en dorado si acertó (comparado por id, como el scoring); ✓/✗ en
 *  cuanto se conoce el primer gol real (en vivo o finalizado); "+N" solo cuando ya
 *  está puntuado. Un solo componente para Partidos, Pronósticos y el modal de otros. */
export function FirstGoalLine({ prediction, match, compact = false }: Props) {
  const { t } = useTranslation();
  const picked   = prediction.first_goal_player;
  const real     = match.first_goal_player;
  const resolved = match.first_goal_player_id != null;
  const hit      = resolved
    && prediction.first_goal_player_id != null
    && prediction.first_goal_player_id === match.first_goal_player_id;
  if (!picked && (compact || !real)) return null;

  return (
    <p className="text-xs text-ucl-silver/50 mt-0.5">
      <span title={t("common.firstGoal")}>⚽ </span>
      {!compact && <span>{t("common.firstGoal")}: </span>}
      {picked
        ? <span className={hit ? "text-ucl-gold font-medium" : "text-ucl-silver/70"}>{picked}</span>
        : <span className="italic">{t("common.noScorer")}</span>}
      {!compact && real && (
        <span className="text-ucl-silver/40">{t("common.realScorer", { name: real })}</span>
      )}
      {resolved && prediction.first_goal_player_id != null && (
        <span className={hit ? "text-ucl-gold" : "text-ucl-silver/40"}> {hit ? "✓" : "✗"}</span>
      )}
      {hit && prediction.is_calculated && (
        <span className="text-ucl-gold font-mono"> +{prediction.first_goal_points}</span>
      )}
    </p>
  );
}
