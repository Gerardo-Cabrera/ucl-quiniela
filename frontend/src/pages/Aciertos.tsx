import { Target, Goal } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useStats } from "@/hooks";
import { Card, Spinner, EmptyState, RankingCard } from "@/components/ui";
import { ShareButton } from "@/components/ShareButton";
import type { UserCount } from "@/types";

interface HitRow {
  match_id: number;
  home_team: string;
  away_team: string;
  value: string;        // goleador o marcador real
  hitters: string[];    // quiénes acertaron (siempre ≥1)
}

/** Lista de partidos con acierto (primer gol o marcador exacto). Fuente única
 *  para no duplicar el render de ambas secciones. */
function HitList({ title, rows }: { title: string; rows: HitRow[] }) {
  const { t } = useTranslation();
  if (rows.length === 0) return null;
  return (
    <Card>
      <h2 className="font-display text-xl mb-4">{title}</h2>
      {/* Los acertantes nunca se recortan: en móvil van en su propia línea bajo el
          partido; en pantallas anchas comparten fila y saltan de línea si hace falta. */}
      <div className="space-y-2">
        {rows.map((r) => (
          <div key={r.match_id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 rounded-lg hover:bg-ucl-blue/20 text-sm">
            <span className="flex-1 min-w-0 text-ucl-white truncate">
              {r.home_team} <span className="text-ucl-silver/40">{t("common.vs")}</span> {r.away_team}
            </span>
            <span className="text-ucl-gold font-medium font-mono shrink-0">{r.value}</span>
            <span className="w-full sm:w-auto sm:flex-1 sm:basis-0 text-xs text-ucl-silver/60 sm:text-right break-words">
              {r.hitters.join(", ")}
            </span>
          </div>
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

  // Texto para compartir: ranking de cada tipo de acierto y qué partidos fueron
  // (marcador o goleador real) con quiénes acertaron. Solo secciones con datos.
  const section = (title: string, ranking: UserCount[], detail: string[]) =>
    ranking.length ? [title, ...ranking.map((u, i) => `${i + 1}. ${u.team_name} — ${u.count}`), ...detail, ""] : [];
  const shareText = [
    `${t("brand.appTitle")} · ${t("aciertos.title")}`, "",
    ...section(t("aciertos.exactScore"), data!.exact_ranking,
      data!.exact_matches.map((m) => `${m.home_team} ${m.score} ${m.away_team}: ${m.hitters.join(", ")}`)),
    ...section(t("aciertos.firstScorer"), data!.first_goal_ranking,
      data!.first_goal_matches.map((m) => `${m.home_team} ${t("common.vs")} ${m.away_team} — ${m.scorer ?? t("common.dash")}: ${m.hitters.join(", ")}`)),
  ].join("\n").trim();

  return (
    <div className="space-y-6 animate-in">
      <div className="flex items-start justify-between gap-3">
        {header}
        <ShareButton text={shareText} ariaLabel={t("aciertos.shareAria")} />
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <RankingCard
          title={t("aciertos.firstScorer")}
          icon={<Goal size={18} className="text-ucl-gold" />}
          rows={data!.first_goal_ranking.map((u) => ({ name: u.team_name, value: u.count }))}
          emptyText={t("aciertos.firstScorerEmpty")}
        />
        <RankingCard
          title={t("aciertos.exactScore")}
          icon={<Target size={18} className="text-ucl-gold" />}
          rows={data!.exact_ranking.map((u) => ({ name: u.team_name, value: u.count }))}
          emptyText={t("aciertos.exactScoreEmpty")}
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
        title={t("aciertos.firstGoalByMatch")}
        rows={data!.first_goal_matches.map((m) => ({
          match_id: m.match_id, home_team: m.home_team, away_team: m.away_team,
          value: m.scorer ?? t("common.dash"), hitters: m.hitters,
        }))}
      />

      <HitList
        title={t("aciertos.exactByMatch")}
        rows={data!.exact_matches.map((m) => ({
          match_id: m.match_id, home_team: m.home_team, away_team: m.away_team,
          value: m.score, hitters: m.hitters,
        }))}
      />
    </div>
  );
}
