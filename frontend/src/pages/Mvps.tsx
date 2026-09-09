import { useState } from "react";
import { Crown } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useMatchdays } from "@/hooks";
import { Card, Spinner, EmptyState, RankingCard, Pills } from "@/components/ui";
import { mvpRanking, useMatchdayLabels, type MatchdayView } from "@/lib/matchdays";
import type { PointsGroup } from "@/types";

export default function Mvps() {
  const { t } = useTranslation();
  const { data, isLoading } = useMatchdays();
  const [view, setView] = useState<MatchdayView>("days");
  const { viewOptions, dayShort, roundTitle, roundDates } = useMatchdayLabels();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  // Histórico: solo grupos ya completos (todos sus partidos jugados y puntuados; un
  // grupo en curso aún puede cambiar de MVP) y con MVP, del más reciente al más antiguo.
  const rows: { key: string; label: string; group: PointsGroup }[] =
    view === "days"
      ? (data?.days ?? []).map((d) => ({ key: d.date, label: dayShort(d.date), group: d }))
      : (data?.rounds ?? []).map((r) => ({
          key: `${r.phase}-${r.round_number}`, label: `${roundTitle(r)} · ${roundDates(r)}`, group: r,
        }));
  const history = rows.filter((row) => row.group.complete && row.group.mvps.length > 0).reverse();

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-4xl text-ucl-gold">{t("mvps.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("mvps.subtitle")}</p>
      </div>

      <Pills options={viewOptions} value={view} onChange={setView} />

      {history.length === 0 ? (
        <EmptyState icon="👑" title={t("mvps.emptyTitle")} description={t("mvps.emptyDescription")} />
      ) : (
        <>
          {/* MVP de cada día / jornada completa */}
          <Card>
            <h2 className="font-display text-xl mb-4 flex items-center gap-2">
              <Crown size={18} className="text-ucl-gold" /> {t(view === "days" ? "mvps.byDayTitle" : "mvps.byRoundTitle")}
            </h2>
            <div className="space-y-2">
              {history.map(({ key, label, group }) => (
                <div key={key} className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-ucl-blue/20">
                  <span className="text-xs text-ucl-silver/60 font-mono capitalize shrink-0">{label}</span>
                  <span className="flex-1 min-w-0 text-sm font-medium text-ucl-gold truncate flex items-center gap-1.5">
                    <Crown size={13} className="shrink-0" /> {group.mvps.join(" · ")}
                  </span>
                  <span className="font-display text-lg text-ucl-gold shrink-0">
                    {group.mvp_points}<span className="text-xs text-ucl-silver/50 font-mono ml-1">{t("common.pts")}</span>
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Ranking: veces como MVP en la vista elegida */}
          <RankingCard
            title={t("mvps.ranking")}
            icon={<Crown size={18} className="text-ucl-gold" />}
            rows={mvpRanking(history.map((row) => row.group))}
            valueSuffix="×"
            emptyText={t("mvps.rankingEmpty")}
          />
        </>
      )}
    </div>
  );
}
