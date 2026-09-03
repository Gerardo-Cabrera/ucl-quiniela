import { useTranslation } from "react-i18next";
import type { Match, Prediction } from "@/types";

interface Props {
  prediction: Prediction;
  match: Match;
  /** Incluir "· Primer gol real: X" en la línea. Partidos lo desactiva porque esa
   *  tarjeta ya muestra el primer gol real en su propia fila (para todos, con o
   *  sin pronóstico); así cada dato va en una fila y nada se repite. */
  showReal?: boolean;
}

/** Línea de primer gol de una tarjeta de pronóstico:
 *  "⚽ Primer gol: elegido · Primer gol real: X ✓ +N".
 *  El elegido va en dorado si acertó (comparado por id, como el scoring); ✓/✗ en
 *  cuanto se conoce el primer gol real (en vivo o finalizado); "+N" solo cuando ya
 *  está puntuado. Un solo componente para Partidos, Pronósticos y el modal de otros. */
export function FirstGoalLine({ prediction, match, showReal = true }: Props) {
  const { t } = useTranslation();
  const picked   = prediction.first_goal_player;
  const real     = match.first_goal_player;
  const resolved = match.first_goal_player_id != null;
  const hit      = resolved
    && prediction.first_goal_player_id != null
    && prediction.first_goal_player_id === match.first_goal_player_id;
  if (!picked && !(showReal && real)) return null;

  return (
    <p className="text-xs text-ucl-silver/50 mt-0.5">
      ⚽ {t("common.firstGoal")}:{" "}
      {picked
        ? <span className={hit ? "text-ucl-gold font-medium" : "text-ucl-silver/70"}>{picked}</span>
        : <span className="italic">{t("common.noScorer")}</span>}
      {showReal && real && (
        <span className="text-ucl-silver/40"> · {t("common.firstGoalReal")}: {real}</span>
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
