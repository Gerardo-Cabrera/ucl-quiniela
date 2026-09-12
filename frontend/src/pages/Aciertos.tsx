import { Target, Goal, Trophy, Equal } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useStats } from "@/hooks";
import { Card, Spinner, EmptyState, RankingCard, DayHeader } from "@/components/ui";
import { ShareButton } from "@/components/ShareButton";
import { bold, bulletWithDetail, shareText } from "@/lib/share";
import { groupByDay } from "@/lib/date";

interface HitRow {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  value: string;        // goleador o marcador real
  hitters: string[];    // quiénes acertaron (siempre ≥1)
}

/** Lista de partidos con acierto, agrupados por fecha con subtítulo, de la más
 *  reciente a la más antigua. Fuente única para todos los tipos de acierto. */
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

  // Tipos de acierto, en el orden de la vista. De esta lista salen los rankings, el
  // detalle por partido y el texto compartido (sin repetir markup por tipo).
  const withScore = (r: HitRow) => `${r.home_team} ${r.value} ${r.away_team}`;
  const kinds = data ? [
    {
      key: "exact", title: t("aciertos.exactScore"), icon: <Target size={18} className="text-ucl-gold" />,
      ranking: data.exact_ranking, rows: data.exact_matches.map((m) => ({ ...m, value: m.score })),
      byMatch: t("aciertos.exactByMatch"), empty: t("aciertos.exactScoreEmpty"),
      shareDetail: t("aciertos.shareExactDetail"), label: withScore,
    },
    {
      key: "first_goal", title: t("aciertos.firstScorer"), icon: <Goal size={18} className="text-ucl-gold" />,
      ranking: data.first_goal_ranking, rows: data.first_goal_matches.map((m) => ({ ...m, value: m.scorer ?? t("common.dash") })),
      byMatch: t("aciertos.firstGoalByMatch"), empty: t("aciertos.firstScorerEmpty"),
      shareDetail: t("aciertos.shareFirstGoalDetail"),
      label: (r: HitRow) => `${r.home_team} ${t("common.vs")} ${r.away_team} — ${r.value}`,
    },
    {
      key: "win", title: t("aciertos.wins"), icon: <Trophy size={18} className="text-ucl-gold" />,
      ranking: data.win_ranking, rows: data.win_matches.map((m) => ({ ...m, value: m.score })),
      byMatch: t("aciertos.winsByMatch"), empty: t("aciertos.winsEmpty"),
      shareDetail: t("aciertos.shareWinsDetail"), label: withScore,
    },
    {
      key: "draw", title: t("aciertos.draws"), icon: <Equal size={18} className="text-ucl-gold" />,
      ranking: data.draw_ranking, rows: data.draw_matches.map((m) => ({ ...m, value: m.score })),
      byMatch: t("aciertos.drawsByMatch"), empty: t("aciertos.drawsEmpty"),
      shareDetail: t("aciertos.shareDrawsDetail"), label: withScore,
    },
  ] : [];
  const hasData = kinds.some((k) => k.ranking.length > 0);

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
  // bloque y, en otro, cada partido acertado con quiénes acertaron en su propia línea
  // y una línea en blanco entre partidos.
  const text = shareText(
    `${t("brand.appTitle")} · ${t("aciertos.title")}`,
    ...kinds.flatMap((k) => k.ranking.length ? [
      [bold(k.title), ...k.ranking.map((u, i) => `${i + 1}. ${u.team_name} — ${u.count}`)],
      [k.shareDetail, k.rows.map((r) => bulletWithDetail(k.label(r), r.hitters.join(", "))).join("\n\n")],
    ] : []),
  );

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between gap-3">
        {header}
        <ShareButton text={text} ariaLabel={t("aciertos.shareAria")} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {kinds.map((k) => (
          <RankingCard
            key={k.key}
            title={k.title}
            icon={k.icon}
            rows={k.ranking.map((u) => ({ name: u.team_name, value: u.count }))}
            emptyText={k.empty}
          />
        ))}
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

      {kinds.map((k) => <HitList key={k.key} title={k.byMatch} rows={k.rows} />)}
    </div>
  );
}
