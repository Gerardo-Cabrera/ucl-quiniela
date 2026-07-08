import { useMyPredictions, useDeletePrediction } from "@/hooks";
import { Spinner, EmptyState, PointsChip, Badge } from "@/components/ui";
import { Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

export default function MyPredictionsPage() {
  const { t } = useTranslation();
  const { data: predictions, isLoading } = useMyPredictions();
  const { mutate: deletePred }           = useDeletePrediction();

  const totalPoints = predictions?.reduce((s, p) => s + p.points_earned, 0) ?? 0;
  const calculated  = predictions?.filter((p) => p.is_calculated).length ?? 0;

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-4xl text-ucl-gold">{t("predictions.title")}</h1>
          <p className="text-ucl-silver/60 text-sm mt-1">{t("predictions.subtitle", { count: predictions?.length ?? 0 })}</p>
        </div>
        {calculated > 0 && (
          <div className="text-right">
            <p className="font-display text-4xl text-ucl-gold">{totalPoints}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("predictions.ptsMatches")}</p>
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !predictions?.length ? (
        <EmptyState
          icon="🎯"
          title={t("predictions.emptyTitle")}
          description={t("predictions.emptyDescription")}
        />
      ) : (
        <div className="space-y-3">
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
                  "card px-5 py-4 flex items-center gap-4",
                  isExact && "border-ucl-gold/30 shadow-[0_0_16px_rgba(201,168,76,0.08)]"
                )}
              >
                {/* Teams logos */}
                <div className="flex items-center gap-2 shrink-0">
                  {match.home_team_logo ? (
                    <img src={match.home_team_logo} alt="" className="w-7 h-7 object-contain" />
                  ) : <span>⚽</span>}
                  {match.away_team_logo ? (
                    <img src={match.away_team_logo} alt="" className="w-7 h-7 object-contain" />
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

                {/* Points / Delete */}
                <div className="shrink-0 flex items-center gap-2">
                  {pred.is_calculated ? (
                    <PointsChip points={pred.points_earned} />
                  ) : !pred.is_calculated && match.status === "scheduled" ? (
                    <button
                      onClick={() => deletePred(pred.id)}
                      className="text-ucl-silver/30 hover:text-red-400 transition-colors p-1"
                      title={t("predictions.delete")}
                    >
                      <Trash2 size={15} />
                    </button>
                  ) : (
                    <span className="text-xs text-ucl-silver/40 font-mono">—</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
