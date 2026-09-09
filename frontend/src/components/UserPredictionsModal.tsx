import { createPortal } from "react-dom";
import { X, Award, Goal } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useUserPredictions, useUserTop8, useUserTournament, useActualTop8 } from "@/hooks";
import { top8Hits } from "@/lib/top8";
import { Spinner, EmptyState, PointsChip } from "@/components/ui";
import { PredictionsByDay } from "@/components/PredictionCard";

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
  const { data: predictions, isLoading: predLoading } = useUserPredictions(userId);
  const { data: top8, isLoading: top8Loading } = useUserTop8(userId);
  const { data: tournament, isLoading: tourLoading } = useUserTournament(userId);
  const actual = useActualTop8().data ?? [];   // Top 8 real, para el resumen de aciertos
  const isLoading = predLoading || top8Loading || tourLoading;
  const hasTop8  = !!top8?.length;
  const hasPreds = !!predictions?.length;
  const hasTournament = !!(tournament && (tournament.mvp_player || tournament.top_scorer_player));

  // Portal al body: escapa del ancestro con transform (`.animate-in`), que rompería
  // el `fixed` y provocaría un scroll en vez de mostrar el modal centrado.
  return createPortal(
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
        ) : !hasTop8 && !hasPreds && !hasTournament ? (
          <EmptyState
            icon="🔒"
            title={t("userPredictions.emptyTitle")}
            description={t("userPredictions.emptyDescription")}
          />
        ) : (
          <div className="space-y-6 overflow-y-auto pr-1 -mr-1">
            {hasTop8 && (
              <section>
                <h3 className="font-display text-lg text-ucl-gold/90 mb-2">
                  {t("userPredictions.top8Title")}
                  {actual.length > 0 && (
                    <span className="ml-2 text-xs font-sans font-normal text-ucl-silver/60">
                      {t("top8.hitsSummary", top8Hits(top8!, actual))}
                    </span>
                  )}
                </h3>
                <div className="space-y-1.5">
                  {top8!.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ucl-blue/15">
                      <span className="font-display text-lg text-ucl-gold/70 w-6 text-center shrink-0">{p.position}</span>
                      <span className="flex-1 text-sm truncate">{p.team_name}</span>
                      {p.is_calculated && <PointsChip points={p.points_earned} />}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {hasTournament && (
              <section>
                <h3 className="font-display text-lg text-ucl-gold/90 mb-2">{t("userPredictions.tournamentTitle")}</h3>
                <div className="space-y-1.5">
                  {tournament!.mvp_player && (
                    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ucl-blue/15">
                      <Award size={15} className="text-ucl-gold/70 shrink-0" />
                      <span className="text-xs text-ucl-silver/50 shrink-0">{t("tournament.mvp")}</span>
                      <span className="flex-1 text-sm truncate text-right sm:text-left">{tournament!.mvp_player}</span>
                      {tournament!.is_calculated && <PointsChip points={tournament!.mvp_points} />}
                    </div>
                  )}
                  {tournament!.top_scorer_player && (
                    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ucl-blue/15">
                      <Goal size={15} className="text-ucl-gold/70 shrink-0" />
                      <span className="text-xs text-ucl-silver/50 shrink-0">{t("tournament.topScorer")}</span>
                      <span className="flex-1 text-sm truncate text-right sm:text-left">{tournament!.top_scorer_player}</span>
                      {tournament!.is_calculated && <PointsChip points={tournament!.top_scorer_points} />}
                    </div>
                  )}
                </div>
              </section>
            )}

            {hasPreds && (
              <section>
                <h3 className="font-display text-lg text-ucl-gold/90 mb-2">{t("userPredictions.predictionsTitle")}</h3>
                {/* Misma tarjeta que Mis Pronósticos, agrupada por jornada (subtítulo con la fecha). */}
                <PredictionsByDay predictions={predictions!} headerClassName="text-base" />
              </section>
            )}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}
