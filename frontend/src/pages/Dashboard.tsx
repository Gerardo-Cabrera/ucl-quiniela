import { useState } from "react";
import { Trophy, Target, Star, Share2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useLeaderboard } from "@/hooks";
import { Card, Spinner, EmptyState } from "@/components/ui";
import { UserPredictionsModal } from "@/components/UserPredictionsModal";
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
    return <EmptyState icon="🏆" title={t("dashboard.emptyTitle")} description={t("dashboard.emptyDescription")} />;
  }

  const myEntry = leaderboard.find((e) => e.team_name === user?.team_name);

  // Comparte la tabla como texto: WhatsApp (u otra app) se abre con el mensaje
  // pre-cargado y el usuario elige el grupo. Reutiliza los datos ya mostrados.
  // Sin emojis (astral/4 bytes): WhatsApp los corrompe en el texto de wa.me.
  const shareWhatsApp = () => {
    const rows = leaderboard.map(
      (e) => `${e.rank}. ${e.team_name} — ${e.total_points} ${t("common.pts")}`,
    );
    const text = `${t("dashboard.shareTitle")}\n\n${rows.join("\n")}`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  };

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
          <button
            onClick={shareWhatsApp}
            aria-label={t("dashboard.shareAria")}
            className="flex items-center gap-1.5 text-xs font-medium text-ucl-silver hover:text-ucl-gold border border-ucl-blue/50 hover:border-ucl-gold/50 rounded-lg px-3 py-1.5 transition-colors shrink-0"
          >
            <Share2 size={14} /> {t("dashboard.share")}
          </button>
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

                {/* Team name */}
                <span className={clsx(
                  "flex-1 text-sm font-medium truncate",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.team_name}
                  {isMe && <span className="ml-2 text-xs text-ucl-gold/60">{t("dashboard.you")}</span>}
                </span>

                {/* Points breakdown */}
                <div className="hidden sm:flex items-center gap-3 text-xs text-ucl-silver/60 font-mono">
                  <span title={t("dashboard.legendMatches")}><Target size={11} className="inline mr-0.5" />{entry.match_points}</span>
                  <span title={t("dashboard.legendTop8")}><Star size={11} className="inline mr-0.5" />{entry.top8_points}</span>
                </div>

                {/* Total */}
                <span className={clsx(
                  "font-display text-2xl w-14 text-right shrink-0",
                  isMe ? "text-ucl-gold" : "text-ucl-white"
                )}>
                  {entry.total_points}
                </span>
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="mt-4 pt-4 border-t border-ucl-blue/30 flex items-center gap-4 text-xs text-ucl-silver/50 font-mono">
          <span><Target size={11} className="inline mr-1" />{t("dashboard.legendMatches")}</span>
          <span><Star size={11} className="inline mr-1" />{t("dashboard.legendTop8")}</span>
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
