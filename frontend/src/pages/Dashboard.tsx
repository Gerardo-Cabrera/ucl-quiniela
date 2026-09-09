import { useState } from "react";
import { Trophy, Star, Award, ListChecks } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useLeaderboard } from "@/hooks";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { UserPredictionsModal } from "@/components/UserPredictionsModal";
import { ShareButton } from "@/components/ShareButton";
import { useAuthStore } from "@/store/authStore";
import { clsx } from "clsx";

const RANK_STYLES = [
  "text-yellow-400",  // 1st
  "text-gray-300",    // 2nd
  "text-amber-600",   // 3rd
];

export default function Dashboard() {
  const { t } = useTranslation();
  const { data: leaderboard, isLoading } = useLeaderboard();
  const { user } = useAuthStore();
  const [selected, setSelected] = useState<{ userId: number; teamName: string } | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!leaderboard?.length) {
    return <EmptyState icon={<img src="/ucl.png" alt="" className="h-24 w-auto" />} title={t("dashboard.emptyTitle")} description={t("dashboard.emptyDescription")} />;
  }

  const myEntry = leaderboard.find((e) => e.team_name === user?.team_name);
  // Los puntos de Top 8 y torneo solo se muestran cuando ya se calcularon: antes
  // serían 0 para todos y se leerían como "no especificado". Hasta entonces la
  // columna del Top 8 indica si ya se eligió.
  const anyTop8Calculated = leaderboard.some((e) => e.top8_calculated);
  const anyTournamentCalculated = leaderboard.some((e) => e.tournament_calculated);

  // La tabla como texto para compartir (reutiliza los datos ya mostrados).
  const shareText = [
    t("dashboard.shareTitle"), "",
    ...leaderboard.map((e) => `${e.rank}. ${e.team_name} — ${e.total_points} ${t("common.pts")}`),
  ].join("\n");

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div>
        <h1 className="font-display text-4xl text-ucl-gold">{t("dashboard.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("brand.edition")}</p>
      </div>

      {/* My summary */}
      {myEntry && (
        <Card gold className="flex items-center justify-between">
          <div>
            <p className="text-xs text-ucl-silver/60 font-mono uppercase mb-1">{t("dashboard.yourPosition")}</p>
            <div className="flex items-center gap-3">
              <span className="font-display text-5xl text-ucl-gold">#{myEntry.rank}</span>
              <div>
                <p className="font-medium text-ucl-white">{myEntry.team_name}</p>
                <p className="text-xs text-ucl-silver/60">{t("dashboard.predictionsCount", { count: myEntry.predictions_count })}</p>
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className="font-display text-5xl text-ucl-gold">{myEntry.total_points}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("dashboard.points")}</p>
          </div>
        </Card>
      )}

      {/* Leaderboard table */}
      <Card>
        <div className="flex items-center justify-between gap-2 mb-5">
          <div className="flex items-center gap-2">
            <Trophy size={18} className="text-ucl-gold" />
            <h2 className="font-display text-2xl">{t("dashboard.classification")}</h2>
          </div>
          <ShareButton text={shareText} ariaLabel={t("dashboard.shareAria")} />
        </div>

        <div className="space-y-2">
          {leaderboard.map((entry, i) => {
            const isMe = entry.team_name === user?.team_name;
            return (
              <button
                key={entry.team_name}
                onClick={() => setSelected({ userId: entry.user_id, teamName: entry.team_name })}
                title={t("dashboard.viewPredictions")}
                className={clsx(
                  "w-full flex items-center gap-4 px-4 py-3 rounded-lg transition-colors text-left",
                  isMe
                    ? "bg-ucl-gold/10 border border-ucl-gold/20 hover:bg-ucl-gold/20"
                    : "hover:bg-ucl-blue/20"
                )}
              >
                {/* Rank */}
                <span className={clsx(
                  "font-display text-xl w-8 text-center shrink-0",
                  i < 3 ? RANK_STYLES[i] : "text-ucl-silver/50"
                )}>
                  {i < 3 ? ["🥇","🥈","🥉"][i] : entry.rank}
                </span>

                {/* Nombre + desglose: en móvil el desglose va debajo del nombre; en
                    pantallas anchas, en línea. Un solo elemento (sin duplicar). */}
                <div className="flex-1 min-w-0 flex flex-col gap-0.5 sm:flex-row sm:items-center sm:gap-4">
                <span className={clsx(
                  "sm:flex-1 text-sm font-medium truncate",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.team_name}
                  {isMe && <span className="ml-2 text-xs text-ucl-gold/60">{t("dashboard.you")}</span>}
                </span>

                {/* Points breakdown */}
                <div className="flex items-center gap-3 text-xs text-ucl-silver/60 font-mono shrink-0">
                  <span title={t("dashboard.legendPredictions")}><ListChecks size={11} className="inline mr-0.5" />{entry.predictions_count}</span>
                  {entry.top8_calculated ? (
                    <span title={t("dashboard.legendTop8")}><Star size={11} className="inline mr-0.5" />{entry.top8_points}</span>
                  ) : (
                    <span title={t("dashboard.legendTop8Chosen", { mark: entry.has_top8 ? "✓" : "✗" })}>
                      <Star size={11} className="inline mr-0.5" />{entry.has_top8 ? "✓" : "✗"}
                    </span>
                  )}
                  {entry.tournament_calculated && (
                    <span title={t("dashboard.legendTournament")}><Award size={11} className="inline mr-0.5" />{entry.tournament_points}</span>
                  )}
                </div>
                </div>

                {/* Total */}
                <span className={clsx(
                  "font-display text-2xl w-16 text-right shrink-0",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.total_points}
                  <span className="ml-1 text-[10px] font-sans text-ucl-silver/50">{t("common.pts")}</span>
                </span>
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t border-ucl-blue/30 flex items-center gap-4 flex-wrap text-xs text-ucl-silver/50 font-mono">
          <span><ListChecks size={11} className="inline mr-1" />{t("dashboard.legendPredictions")}</span>
          <span><Star size={11} className="inline mr-1" />{anyTop8Calculated ? t("dashboard.legendTop8") : t("dashboard.legendTop8Chosen", { mark: "✓ / ✗" })}</span>
          {anyTournamentCalculated && <span><Award size={11} className="inline mr-1" />{t("dashboard.legendTournament")}</span>}
        </div>
      </Card>

      {selected && (
        <UserPredictionsModal
          userId={selected.userId}
          teamName={selected.teamName}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
