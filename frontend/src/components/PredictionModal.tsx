import { useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X, Minus, Plus, Check } from "lucide-react";
import { clsx } from "clsx";
import { useTranslation } from "react-i18next";
import { groupSquad } from "@/lib/players";
import type { Match, Prediction } from "@/types";
import { useSavePrediction, useMatchPlayers } from "@/hooks";
import { Spinner } from "@/components/ui";

interface Props {
  match: Match;
  prediction?: Prediction;
  onClose: () => void;
}

function ScoreInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={() => onChange(Math.max(0, value - 1))}
        className="w-8 h-8 rounded-full border border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold transition-colors flex items-center justify-center"
      >
        <Minus size={14} />
      </button>
      <span className="font-display text-4xl text-ucl-white w-10 text-center">{value}</span>
      <button
        onClick={() => onChange(value + 1)}
        className="w-8 h-8 rounded-full border border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold transition-colors flex items-center justify-center"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}

/** Fila seleccionable de la lista de primer goleador (jugador o "sin pronóstico"). */
function SquadOption({ selected, onClick, className, children }: {
  selected: boolean;
  onClick: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      onClick={onClick}
      className={clsx(
        "w-full flex items-center justify-between gap-2 px-3 py-2 text-sm text-left transition-colors",
        selected ? "bg-ucl-gold/15 text-ucl-gold font-medium" : "text-ucl-white hover:bg-ucl-blue/30",
        className,
      )}
    >
      <span className="truncate">{children}</span>
      {selected && <Check size={14} className="shrink-0" />}
    </button>
  );
}

export function PredictionModal({ match, prediction, onClose }: Props) {
  const { t } = useTranslation();
  const [homeScore, setHomeScore] = useState(prediction?.predicted_home ?? 0);
  const [awayScore, setAwayScore]  = useState(prediction?.predicted_away ?? 0);
  const [firstGoalPlayerId, setFirstGoalPlayerId] = useState<number | null>(
    prediction?.first_goal_player_id ?? null,
  );
  const { mutate: save, isPending, isSuccess, isError } = useSavePrediction();
  const { data: players = [], isLoading: playersLoading } = useMatchPlayers(match.id);

  // Lista agrupada por equipo (local, visitante) y posición (portero → delantero).
  // Es una lista propia y no un <select>: el selector nativo del móvil ignora los
  // estilos de las opciones, así que las cabeceras no podrían leerse bien ahí.
  const squad = groupSquad(players, [match.home_team, match.away_team]);
  const selectedName = players.find((p) => p.api_player_id === firstGoalPlayerId)?.name;

  const handleSave = () => {
    save({
      match_id:       match.id,
      predicted_home: homeScore,
      predicted_away: awayScore,
      first_goal_player_id: firstGoalPlayerId ?? undefined,
    }, { onSuccess: () => setTimeout(onClose, 800) });
  };

  // Portal al body: escapa del ancestro con transform (`.animate-in`), que rompería
  // el `fixed` y provocaría un scroll en vez de mostrar el modal centrado.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative w-full max-w-md card border-ucl-gold/25 p-6 shadow-2xl animate-in">
        {/* Close */}
        <button onClick={onClose} className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors">
          <X size={20} />
        </button>

        <h2 className="font-display text-2xl text-ucl-gold mb-1">
          {prediction ? t("predictionModal.titleEdit") : t("predictionModal.titleNew")}
        </h2>
        <p className="text-ucl-silver/60 text-sm mb-6">
          {match.home_team} vs {match.away_team}
        </p>

        {/* Score picker */}
        <div className="flex items-center justify-between gap-4 bg-ucl-navy/60 rounded-xl p-5 mb-5">
          <div className="flex flex-col items-center gap-3">
            {match.home_team_logo && <img src={match.home_team_logo} alt="" className="w-10 h-10 object-contain" />}
            <span className="text-xs text-ucl-silver/70 text-center">{match.home_team}</span>
            <ScoreInput value={homeScore} onChange={setHomeScore} />
          </div>
          <span className="font-display text-2xl text-ucl-silver/30">-</span>
          <div className="flex flex-col items-center gap-3">
            {match.away_team_logo && <img src={match.away_team_logo} alt="" className="w-10 h-10 object-contain" />}
            <span className="text-xs text-ucl-silver/70 text-center">{match.away_team}</span>
            <ScoreInput value={awayScore} onChange={setAwayScore} />
          </div>
        </div>

        {/* First goal scorer */}
        <div className="mb-6">
          <p className="text-xs text-ucl-silver/70 mb-2 font-mono uppercase tracking-wider">
            {t("predictionModal.firstScorer")}
            {selectedName && <span className="ml-2 normal-case text-ucl-gold">· {selectedName}</span>}
          </p>
          {playersLoading ? (
            <div className="flex items-center gap-2 text-ucl-silver/50 text-sm"><Spinner size="sm" /> {t("predictionModal.loadingPlayers")}</div>
          ) : players.length === 0 ? (
            <p className="text-ucl-silver/40 text-sm">{t("predictionModal.noSquads")}</p>
          ) : (
            <div
              role="listbox"
              aria-label={t("predictionModal.firstScorer")}
              className="rounded-lg border border-ucl-blue/60 bg-ucl-navy/60 max-h-56 overflow-y-auto"
            >
              <SquadOption
                selected={firstGoalPlayerId === null}
                onClick={() => setFirstGoalPlayerId(null)}
                className="italic text-ucl-silver/60"
              >
                {t("predictionModal.noPrediction")}
              </SquadOption>
              {squad.map((team) => (
                <div key={team.team}>
                  {/* Cabecera de equipo: fija arriba mientras se hace scroll en su bloque. */}
                  <div className="sticky top-0 bg-ucl-navy px-3 py-1.5 font-display text-base text-ucl-gold border-y border-ucl-blue/40">
                    {team.team}
                  </div>
                  {team.positions.map((g) => (
                    <div key={g.position}>
                      <div className="px-3 pt-2 pb-1 text-[11px] font-mono uppercase tracking-wider text-ucl-silver/80">
                        {t(`position.${g.position || "unknown"}`)}
                      </div>
                      {g.players.map((p) => (
                        <SquadOption
                          key={p.api_player_id}
                          selected={firstGoalPlayerId === p.api_player_id}
                          onClick={() => setFirstGoalPlayerId(p.api_player_id)}
                          className="pl-6"
                        >
                          {p.name}
                        </SquadOption>
                      ))}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          onClick={handleSave}
          disabled={isPending || isSuccess}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isPending ? <><Spinner size="sm" /> {t("predictionModal.saving")}</> :
           isSuccess  ? t("predictionModal.saved") :
           t("predictionModal.save")}
        </button>

        {isError && (
          <p className="mt-3 text-red-400 text-sm text-center">
            {t("predictionModal.error")}
          </p>
        )}
      </div>
    </div>,
    document.body,
  );
}
