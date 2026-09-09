import type { ReactNode } from "react";
import { format } from "date-fns";
import { useTranslation } from "react-i18next";
import type { Prediction } from "@/types";
import { Badge, DayHeader, PointsChip, TeamLogo } from "@/components/ui";
import { FirstGoalLine } from "@/components/FirstGoalLine";
import { groupByDay } from "@/lib/date";
import { clsx } from "clsx";

/** Tarjeta de un pronóstico (solo presentación), compartida por Mis Pronósticos y el
 *  modal de pronósticos de otro participante (Tabla General) para no duplicar el
 *  diseño. Uniforme a cualquier ancho: cabecera con fase y hora (nunca se parten);
 *  los equipos, cada escudo junto al suyo, ocupan su propia fila en pantallas
 *  estrechas y comparten fila con el marcador en las anchas; primer gol al pie.
 *  `action`: hueco de la derecha mientras no hay puntos (p. ej. borrar en la propia). */
export function PredictionCard({ prediction: pred, action }: { prediction: Prediction; action?: ReactNode }) {
  const { t } = useTranslation();
  const match = pred.match;
  const isExact =
    pred.is_calculated &&
    pred.predicted_home === match.home_score &&
    pred.predicted_away === match.away_score;
  const team = (name: string, logo: string | null) => (
    <span className="inline-flex items-center gap-1.5">
      <TeamLogo src={logo} className="w-6 h-6" />{name}
    </span>
  );

  return (
    <div className={clsx(
      "card px-4 py-3 sm:px-5 sm:py-4",
      isExact && "border-ucl-gold/30 shadow-[0_0_16px_rgba(201,168,76,0.08)]",
    )}>
      {/* Cabecera: fase + hora del partido */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <Badge variant={match.phase === "league" ? "blue" : "gold"}>{t(`phase.${match.phase}`)}</Badge>
        <span className="text-xs text-ucl-silver/50 font-mono">{format(new Date(match.match_date), "HH:mm")}</span>
      </div>

      {/* Cuerpo: equipos · pronóstico (y marcador real en cuanto lo hay) · puntos/acción */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p className="w-full sm:w-auto sm:flex-1 min-w-0 text-sm font-medium flex flex-wrap items-center gap-x-1.5 gap-y-1">
          {team(match.home_team, match.home_team_logo)}
          <span className="text-ucl-silver/40">{t("common.vs")}</span>
          {team(match.away_team, match.away_team_logo)}
        </p>
        <div className="ml-auto text-center shrink-0">
          <p className={clsx("font-mono font-bold text-lg", isExact ? "text-ucl-gold" : "text-ucl-white")}>
            {pred.predicted_home} - {pred.predicted_away}
          </p>
          {match.home_score != null && match.away_score != null && (
            <p className="text-xs text-ucl-silver/50 font-mono">
              {t("predictions.real", { home: match.home_score, away: match.away_score })}
            </p>
          )}
        </div>
        <div className="shrink-0">
          {pred.is_calculated
            ? <PointsChip points={pred.points_earned} />
            : (action ?? <span className="text-xs text-ucl-silver/40 font-mono">—</span>)}
        </div>
      </div>

      <FirstGoalLine prediction={pred} match={match} className="mt-3" />
    </div>
  );
}

/** Pronósticos agrupados por jornada (cabecera con la fecha), de la más reciente a
 *  la más antigua. `action(pred)`: hueco de cada tarjeta (ver PredictionCard). */
export function PredictionsByDay({ predictions, action, headerClassName }: {
  predictions: Prediction[];
  action?: (pred: Prediction) => ReactNode;
  headerClassName?: string;
}) {
  return (
    <div className="space-y-6">
      {groupByDay(predictions, (p) => p.match.match_date, "desc").map((group) => (
        <section key={group.day}>
          <DayHeader date={group.date} className={headerClassName} />
          <div className="space-y-3">
            {group.items.map((pred) => (
              <PredictionCard key={pred.id} prediction={pred} action={action?.(pred)} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
