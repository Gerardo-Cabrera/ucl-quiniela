import { Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Match, Prediction } from "@/types";

/** Línea de primer gol de una tarjeta de pronóstico: el jugador elegido y, cuando el
 *  partido ya tiene primer gol real, si se acertó (dorado + check y, ya puntuado, los
 *  puntos que dio; comparado por id, como el scoring) o quién lo anotó realmente. Un
 *  solo componente para todas las tarjetas (Partidos, Pronósticos y modal de otros). */
export function FirstGoalLine({ prediction, match }: { prediction: Prediction; match: Match }) {
  const { t } = useTranslation();
  const picked = prediction.first_goal_player;
  const real   = match.first_goal_player;
  const hit    = picked != null && match.first_goal_player_id != null
    && prediction.first_goal_player_id === match.first_goal_player_id;
  if (!picked && !real) return null;

  return (
    <div className="text-xs mt-0.5">
      {picked && (
        <div className={hit ? "text-ucl-gold font-medium" : "text-ucl-silver/60"}>
          {t("common.firstGoalPick", { player: picked })}
          {hit && <Check size={12} className="inline ml-1 align-text-bottom" />}
          {hit && prediction.is_calculated && (
            <span className="ml-1 font-mono">+{prediction.first_goal_points}</span>
          )}
        </div>
      )}
      {real && !hit && (
        <div className="text-ucl-silver/50">{t("common.firstGoalReal", { player: real })}</div>
      )}
    </div>
  );
}
