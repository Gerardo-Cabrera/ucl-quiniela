import { Target, Goal } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useStats } from "@/hooks";
import { Card, Spinner, EmptyState, RankingCard, DayHeader } from "@/components/ui";
import { groupByDay } from "@/lib/date";
import { ShareButton } from "@/components/ShareButton";
import { bold, bulletWithDetail, shareText } from "@/lib/share";
import type { UserCount } from "@/types";

interface HitRow {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  value: string;        // goleador o marcador real
  hitters: string[];    // quiénes acertaron (siempre ≥1)
}

/** Lista de partidos con acierto (marcador exacto o primer gol), agrupados por
 *  fecha con subtítulo, de la más reciente a la más antigua. Fuente única para no
 *  duplicar el render de ambas secciones. */
function HitList({ title, rows }: { title: string; rows: HitRow[] }) {
  const { t } = useTranslation();
  if (rows.length === 0) return null;
  return (
    <Card>
      <h2 className="font-display text-xl mb-4">{title}</h2>
      <div className="space-y-5">
        {groupByDay(rows, (r) => r.match_date, "desc").map((group) => (
          <section key={group.day}>
            <DayHeader date={group.date} className="text-base" />
            {/* Nada se recorta: en pantallas estrechas el partido, el goleador (o marcador)
                y los acertantes van en líneas sucesivas; en las anchas comparten fila. */}
            <div className="space-y-2">
              {group.items.map((r) => (
                <div key={r.match_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 rounded-lg hover:bg-ucl-blue/20 text-sm">
                  <span className="w-full sm:w-auto sm:flex-1 min-w-0 text-ucl-white">
                    {r.home_team} <span className="text-ucl-silver/40">{t("common.vs")}</span> {r.away_team}
                  </span>
                  <span className="text-ucl-gold font-medium font-mono">{r.value}</span>
                  <span className="w-full sm:w-auto sm:flex-1 sm:basis-0 text-xs text-ucl-silver/60 sm:text-right break-words">
                    {r.hitters.join(", ")}
                  </span>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </Card>
  );
}

export default function Aciertos() {
  const { t } = useTranslation();
  const { data, isLoading } = useStats();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  const hasData =
    data &&
    (data.first_goal_ranking.length ||
      data.exact_ranking.length ||
      data.first_goal_matches.length ||
      data.exact_matches.length);

  // Encabezado
  const header = (
    <div>
      <h1 className="font-display text-4xl text-ucl-gold">{t("aciertos.title")}</h1>
      <p className="text-ucl-silver/60 text-sm mt-1">{t("aciertos.subtitle")}</p>
    </div>
  );

  if (!hasData) {
    return (
      <div className="space-y-6 animate-in">
        {header}
        <EmptyState icon="🎯" title={t("aciertos.emptyTitle")} description={t("aciertos.emptyDescription")} />
      </div>
    );
  }

  // Texto para compartir, por tipo de acierto (solo si hay datos): el ranking en un
  // bloque y, en otro, cada partido acertado (marcador o goleador real) con quiénes
  // acertaron en su propia línea y una línea en blanco entre partidos.
  const section = (title: string, ranking: UserCount[], detailTitle: string, detail: string[]) =>
    ranking.length
      ? [[bold(title), ...ranking.map((u, i) => `${i + 1}. ${u.team_name} — ${u.count}`)], [detailTitle, detail.join("\n\n")]]
      : [];
  const text = shareText(
    `${t("brand.appTitle")} · ${t("aciertos.title")}`,
    ...section(t("aciertos.exactScore"), data!.exact_ranking, t("aciertos.shareExactDetail"),
      data!.exact_matches.map((m) => bulletWithDetail(`${m.home_team} ${m.score} ${m.away_team}`, m.hitters.join(", ")))),
    ...section(t("aciertos.firstScorer"), data!.first_goal_ranking, t("aciertos.shareFirstGoalDetail"),
      data!.first_goal_matches.map((m) =>
        bulletWithDetail(`${m.home_team} ${t("common.vs")} ${m.away_team} — ${m.scorer ?? t("common.dash")}`, m.hitters.join(", ")))),
  );

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between gap-3">
        {header}
        <ShareButton text={text} ariaLabel={t("aciertos.shareAria")} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <RankingCard
          title={t("aciertos.exactScore")}
          icon={<Target size={18} className="text-ucl-gold" />}
          rows={data!.exact_ranking.map((u) => ({ name: u.team_name, value: u.count }))}
          emptyText={t("aciertos.exactScoreEmpty")}
        />
        <RankingCard
          title={t("aciertos.firstScorer")}
          icon={<Goal size={18} className="text-ucl-gold" />}
          rows={data!.first_goal_ranking.map((u) => ({ name: u.team_name, value: u.count }))}
          emptyText={t("aciertos.firstScorerEmpty")}
        />
      </div>

      {data!.top_scores.length > 0 && (
        <Card>
          <h2 className="font-display text-xl mb-2">{t("aciertos.topScore")}</h2>
          <div className="flex flex-wrap gap-2">
            {data!.top_scores.map((s) => (
              <span key={s.score} className="font-mono text-lg text-ucl-gold bg-ucl-gold/10 border border-ucl-gold/30 rounded-lg px-3 py-1">
                {s.score} <span className="text-ucl-silver/60 text-sm">×{s.count}</span>
              </span>
            ))}
          </div>
        </Card>
      )}

      <HitList
        title={t("aciertos.exactByMatch")}
        rows={data!.exact_matches.map((m) => ({ ...m, value: m.score }))}
      />

      <HitList
        title={t("aciertos.firstGoalByMatch")}
        rows={data!.first_goal_matches.map((m) => ({ ...m, value: m.scorer ?? t("common.dash") }))}
      />
    </div>
  );
}
