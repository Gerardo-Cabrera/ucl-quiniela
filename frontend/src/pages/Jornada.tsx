import { useState } from "react";
import { Crown } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslation } from "react-i18next";
import { useMatchdays } from "@/hooks";
import { Card, Spinner, EmptyState, PointsChip, Pills } from "@/components/ui";
import { ShareButton } from "@/components/ShareButton";
import { isoDayToDate } from "@/lib/date";
import type { PointsGroup, RoundEntry } from "@/types";
import { clsx } from "clsx";

type View = "days" | "rounds";

/** Tarjeta de un grupo de puntos (un día o una jornada completa): título, MVP(s),
 *  compartir (solo cuando todos sus partidos se jugaron y puntuaron) y la tabla. */
function GroupCard({ title, subtitle, group }: { title: string; subtitle?: string; group: PointsGroup }) {
  const { t } = useTranslation();
  const pts = (n: number) => `${n} ${t("common.pts")}`;
  const shareText = [
    `${t("brand.appTitle")} · ${title}${subtitle ? ` (${subtitle})` : ""}`,
    group.mvps.length ? `${t("jornada.mvpLabel")}: ${group.mvps.join(" · ")} — ${pts(group.mvp_points)}` : "",
    "",
    ...group.entries.map((e, i) => `${i + 1}. ${e.team_name} — ${pts(e.points)}`),
  ].join("\n");

  return (
    <Card>
      <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between mb-4">
        <div className="min-w-0">
          <h2 className="font-display text-lg sm:text-xl capitalize">{title}</h2>
          {subtitle && <p className="text-xs text-ucl-silver/50 font-mono">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {group.mvps.length > 0 && (
            <span className="inline-flex items-center gap-1.5 text-ucl-gold text-xs font-semibold border border-ucl-gold/40 bg-ucl-gold/10 rounded-full px-2.5 py-1 shrink-0 max-w-full">
              <Crown size={13} className="shrink-0" /> {t("jornada.mvpLabel")}: {group.mvps.join(" · ")}
            </span>
          )}
          <ShareButton
            text={shareText}
            ariaLabel={t("jornada.shareAria")}
            disabled={!group.complete}
            disabledTitle={t("jornada.shareLocked")}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        {group.entries.map((e) => {
          const isMvp = group.mvp_points > 0 && e.points === group.mvp_points;
          return (
            <div
              key={e.user_id}
              className={clsx(
                "flex items-center justify-between gap-3 px-3 py-2 rounded-lg",
                isMvp ? "bg-ucl-gold/10 border border-ucl-gold/20" : "hover:bg-ucl-blue/20"
              )}
            >
              <span className={clsx(
                "flex-1 min-w-0 text-sm font-medium truncate flex items-center gap-1.5",
                isMvp ? "text-ucl-gold" : "text-ucl-white"
              )}>
                {isMvp && <Crown size={13} className="shrink-0" />}
                {e.team_name}
              </span>
              <PointsChip points={e.points} />
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function Jornada() {
  const { t } = useTranslation();
  const { data, isLoading } = useMatchdays();
  const [view, setView] = useState<View>("days");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  // Encabezado
  const header = (
    <div>
      <h1 className="font-display text-4xl text-ucl-gold">{t("jornada.title")}</h1>
      <p className="text-ucl-silver/60 text-sm mt-1">{t("jornada.subtitle")}</p>
    </div>
  );

  if (!data?.days.length) {
    return (
      <div className="space-y-6 animate-in">
        {header}
        <EmptyState icon="📅" title={t("jornada.emptyTitle")} description={t("jornada.emptyDescription")} />
      </div>
    );
  }

  // El backend los envía ascendentes; se muestran del más reciente al más antiguo.
  const days = [...data.days].reverse();
  const rounds = [...data.rounds].reverse();
  const dayTitle = (day: string) => format(isoDayToDate(day), "EEEE d 'de' MMMM", { locale: es });
  // "Jornada N" en fase de liga; en eliminatorias, la fase. Subtítulo: sus días.
  const roundTitle = (r: RoundEntry) =>
    r.round_number != null ? t("jornada.round", { n: r.round_number }) : t(`phase.${r.phase}`);
  const roundDates = (r: RoundEntry) => {
    const fmt = (d: string) => format(isoDayToDate(d), "d MMM", { locale: es });
    return r.start === r.end ? fmt(r.start) : `${fmt(r.start)} – ${fmt(r.end)}`;
  };

  return (
    <div className="space-y-6 animate-in">
      {header}

      <Pills
        options={[
          { value: "days", label: t("jornada.byDay") },
          { value: "rounds", label: t("jornada.byRound") },
        ]}
        value={view}
        onChange={setView}
      />

      {view === "days"
        ? days.map((d) => <GroupCard key={d.date} title={dayTitle(d.date)} group={d} />)
        : rounds.map((r) => (
            <GroupCard key={`${r.phase}-${r.round_number}`} title={roundTitle(r)} subtitle={roundDates(r)} group={r} />
          ))}
    </div>
  );
}
