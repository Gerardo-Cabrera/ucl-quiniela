import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { X, Minus, Plus } from "lucide-react";
import { useTranslation } from "react-i18next";
import { PlayerPicker } from "@/components/PlayerPicker";
import type { Match, Prediction } from "@/types";
import { useSavePrediction, useMatchPlayers } from "@/hooks";
import { Spinner } from "@/components/ui";
import { apiErrorMessage } from "@/lib/apiError";

// Tope de goles por equipo: el mismo que valida el backend (PredictionCreate, le=20).
const MAX_SCORE = 20;

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
        onClick={() => onChange(Math.min(MAX_SCORE, value + 1))}
        className="w-8 h-8 rounded-full border border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold hover:text-ucl-gold transition-colors flex items-center justify-center"
      >
        <Plus size={14} />
      </button>
    </div>
  );
}

export function PredictionModal({ match, prediction, onClose }: Props) {
  const { t } = useTranslation();
  const [homeScore, setHomeScore] = useState(prediction?.predicted_home ?? 0);
  const [awayScore, setAwayScore]  = useState(prediction?.predicted_away ?? 0);
  const [firstGoalPlayerId, setFirstGoalPlayerId] = useState<number | null>(
    prediction?.first_goal_player_id ?? null,
  );
  const { mutate: save, isPending, isSuccess, isError, error } = useSavePrediction();
  const { data: players = [], isLoading: playersLoading } = useMatchPlayers(match.id);

  // Sin goles en el marcador no hay primer gol: el selector se oculta y se limpia
  // la elección, para no enviar un dato oculto e incoherente (el backend también lo
  // rechaza). Con goles, el goleador sigue siendo opcional.
  const hasGoals = homeScore + awayScore > 0;
  useEffect(() => {
    if (!hasGoals) setFirstGoalPlayerId(null);
  }, [hasGoals]);

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

      {/* Modal: nunca más alto que la pantalla. Es una columna flex cuyos hijos directos
          son todos los bloques del formulario (los contenedores intermedios van con
          `contents`): ninguno puede encogerse por debajo de su contenido salvo la
          cuadrícula de jugadores, que cede hasta su mínimo y se desplaza por dentro. Así
          el botón de guardar queda a la vista, y si aun así no cabe (pantallas muy bajas)
          se desplaza el modal entero en vez de montarse unos bloques sobre otros. */}
      <div className="relative w-full max-w-md max-h-[calc(100dvh-2rem)] overflow-y-auto flex flex-col card border-ucl-gold/25 p-6 shadow-2xl animate-in">
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
        <div className="shrink-0 flex items-center justify-between gap-4 bg-ucl-navy/60 rounded-xl p-5 mb-5">
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

        {/* First goal scorer: solo con goles en el marcador (y aun así opcional) */}
        {hasGoals && (
        <div className="contents">
          <label className="block shrink-0 text-xs text-ucl-silver/70 mb-2 font-mono uppercase tracking-wider">
            {t("predictionModal.firstScorer")}
          </label>
          {playersLoading ? (
            <div className="mb-6 flex items-center gap-2 text-ucl-silver/50 text-sm"><Spinner size="sm" /> {t("predictionModal.loadingPlayers")}</div>
          ) : players.length === 0 ? (
            <p className="mb-6 text-ucl-silver/40 text-sm">{t("predictionModal.noSquads")}</p>
          ) : (
            <PlayerPicker
              players={players}
              teams={[
                { name: match.home_team, logo: match.home_team_logo },
                { name: match.away_team, logo: match.away_team_logo },
              ]}
              value={firstGoalPlayerId}
              onChange={setFirstGoalPlayerId}
              matchId={match.id}
            />
          )}
        </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSave}
          disabled={isPending || isSuccess}
          className="btn-primary w-full shrink-0 flex items-center justify-center gap-2"
        >
          {isPending ? <><Spinner size="sm" /> {t("predictionModal.saving")}</> :
           isSuccess  ? t("predictionModal.saved") :
           t("predictionModal.save")}
        </button>

        {/* El motivo que da el backend (plazo de la jornada cerrado, partido ya empezado,
            sin conexión...): "intenta de nuevo" a secas invitaba a repetir algo que no
            puede salir. El texto genérico queda de respaldo. */}
        {isError && (
          <p role="alert" className="mt-3 shrink-0 text-red-400 text-sm text-center">
            {apiErrorMessage(error, t("predictionModal.error"))}
          </p>
        )}
      </div>
    </div>,
    document.body,
  );
}
