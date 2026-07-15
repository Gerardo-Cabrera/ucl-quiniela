import { X } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { useUserPredictions } from "@/hooks";
import { Spinner, EmptyState, PointsChip, Badge } from "@/components/ui";
import { clsx } from "clsx";

interface Props {
  userId: number;
  teamName: string;
  onClose: () => void;
}

/** Pronósticos de otro participante, revelados por jornada iniciada (el backend
 *  solo devuelve los de días cuyo primer partido ya arrancó). Vista de solo
 *  lectura: sin editar ni borrar. */
export function UserPredictionsModal({ userId, teamName, onClose }: Props) {
  const { t } = useTranslation();
  const { data: predictions, isLoading } = useUserPredictions(userId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-lg card border-ucl-gold/25 p-6 shadow-2xl animate-in max-h-[85vh] flex flex-col">
        <button
          onClick={onClose}
          aria-label={t("common.close")}
          className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors"
        >
          <X size={20} />
        </button>

        <h2 className="font-display text-2xl text-ucl-gold mb-1 pr-8">{teamName}</h2>
        <p className="text-ucl-silver/60 text-sm mb-5">{t("userPredictions.subtitle")}</p>

        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner size="lg" /></div>
        ) : !predictions?.length ? (
          <EmptyState
            icon="🔒"
            title={t("userPredictions.emptyTitle")}
            description={t("userPredictions.emptyDescription")}
          />
        ) : (
          <div className="space-y-3 overflow-y-auto pr-1 -mr-1">
            {predictions.map((pred) => {
              const match = pred.match;
              const isExact =
                pred.is_calculated &&
                pred.predicted_home === match.home_score &&
                pred.predicted_away === match.away_score;

              return (
                <div
                  key={pred.id}
                  className={clsx(
                    "card px-4 py-3 flex items-center gap-3",
                    isExact && "border-ucl-gold/30 shadow-[0_0_16px_rgba(201,168,76,0.08)]"
                  )}
                >
                  {/* Teams logos */}
                  <div className="flex items-center gap-2 shrink-0">
                    {match.home_team_logo ? (
                      <img src={match.home_team_logo} alt="" className="w-6 h-6 object-contain" />
                    ) : <span>⚽</span>}
                    {match.away_team_logo ? (
                      <img src={match.away_team_logo} alt="" className="w-6 h-6 object-contain" />
                    ) : <span>⚽</span>}
                  </div>

                  {/* Match info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {match.home_team} <span className="text-ucl-silver/40">{t("common.vs")}</span> {match.away_team}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-ucl-silver/50 font-mono">
                        {format(new Date(match.match_date), "d MMM", { locale: es })}
                      </span>
                      <Badge variant={match.phase === "league" ? "blue" : "gold"}>
                        {t(`phase.${match.phase}`)}
                      </Badge>
                    </div>
                  </div>

                  {/* Prediction */}
                  <div className="text-center shrink-0">
                    <p className={clsx(
                      "font-mono font-bold text-lg",
                      isExact ? "text-ucl-gold" : "text-ucl-white"
                    )}>
                      {pred.predicted_home} - {pred.predicted_away}
                    </p>
                    {match.status === "finished" && (
                      <p className="text-xs text-ucl-silver/50 font-mono">
                        {t("predictions.real", { home: match.home_score, away: match.away_score })}
                      </p>
                    )}
                  </div>

                  {/* Points */}
                  {pred.is_calculated && (
                    <div className="shrink-0">
                      <PointsChip points={pred.points_earned} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
