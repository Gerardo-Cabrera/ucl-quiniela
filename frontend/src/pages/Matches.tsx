import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMatches, useMyPredictions, usePredictionOverride, useSetPredictionOverride } from "@/hooks";
import { useAuthStore } from "@/store/authStore";
import { MatchCard } from "@/components/MatchCard";
import { PredictionModal } from "@/components/PredictionModal";
import { Spinner, EmptyState } from "@/components/ui";
import type { Match, MatchPhase, MatchStatus } from "@/types";
import { clsx } from "clsx";

const PHASES: (MatchPhase | "all")[] = [
  "all", "league", "knockout_playoffs", "round_of_16", "quarter_finals", "semi_finals", "final",
];

const STATUSES: (MatchStatus | "all")[] = ["all", "scheduled", "live", "finished"];

/** Interruptor admin de prórroga de pronósticos. Se auto-oculta si no eres admin. */
function AdminPredictionToggle() {
  const { t } = useTranslation();
  const isAdmin = useAuthStore((s) => s.user?.is_admin ?? false);
  const { data } = usePredictionOverride(isAdmin);
  const { mutate, isPending } = useSetPredictionOverride();

  if (!isAdmin || !data) return null;
  const { enabled, lead_minutes } = data;

  return (
    <div className="card px-4 py-3 flex items-center gap-3">
      <button
        role="switch"
        aria-checked={enabled}
        aria-label={t("matches.overrideAria")}
        disabled={isPending}
        onClick={() => mutate(!enabled)}
        className={clsx(
          "relative w-11 h-6 rounded-full transition-colors shrink-0 disabled:opacity-50",
          enabled ? "bg-ucl-gold" : "bg-ucl-blue/60"
        )}
      >
        <span
          className={clsx(
            "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform",
            enabled && "translate-x-5"
          )}
        />
      </button>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ucl-white">{t("matches.overrideLabel")}</p>
        <p className="text-xs text-ucl-silver/60">
          {enabled ? t("matches.overrideOn") : t("matches.overrideOff", { lead: lead_minutes })}
        </p>
      </div>
    </div>
  );
}

export default function MatchesPage() {
  const { t } = useTranslation();
  const [phase, setPhase]   = useState<MatchPhase | "all">("all");
  const [status, setStatus] = useState<MatchStatus | "all">("scheduled");
  const [selected, setSelected] = useState<Match | null>(null);

  const { data: matches, isLoading } = useMatches({
    phase:  phase  !== "all" ? phase  : undefined,
    status: status !== "all" ? status : undefined,
  });

  const { data: predictions } = useMyPredictions();

  const predictionByMatch = Object.fromEntries(
    (predictions ?? []).map((p) => [p.match_id, p])
  );

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-4xl text-ucl-gold">{t("matches.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("brand.edition")}</p>
      </div>

      <AdminPredictionToggle />

      {/* Filters */}
      <div className="space-y-3">
        <div className="flex gap-2 flex-wrap">
          {PHASES.map((value) => (
            <button
              key={value}
              onClick={() => setPhase(value)}
              className={clsx(
                "px-3 py-1.5 rounded-full text-xs font-mono transition-all duration-150",
                phase === value
                  ? "bg-ucl-gold text-ucl-navy font-bold"
                  : "border border-ucl-blue/50 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold"
              )}
            >
              {value === "all" ? t("matches.filterAll") : t(`matches.phaseFilter.${value}`)}
            </button>
          ))}
        </div>
        <div className="flex gap-2 flex-wrap">
          {STATUSES.map((value) => (
            <button
              key={value}
              onClick={() => setStatus(value)}
              className={clsx(
                "px-3 py-1.5 rounded-full text-xs font-mono transition-all duration-150",
                status === value
                  ? "bg-ucl-blue text-ucl-white font-bold"
                  : "border border-ucl-blue/50 text-ucl-silver hover:border-ucl-silver"
              )}
            >
              {value === "all" ? t("matches.filterAll") : t(`matches.statusFilter.${value}`)}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : !matches?.length ? (
        <EmptyState icon="📅" title={t("matches.emptyTitle")} description={t("matches.emptyDescription")} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {matches.map((match) => (
            <MatchCard
              key={match.id}
              match={match}
              prediction={predictionByMatch[match.id]}
              onPredict={setSelected}
            />
          ))}
        </div>
      )}

      {selected && (
        <PredictionModal
          match={selected}
          prediction={predictionByMatch[selected.id]}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
