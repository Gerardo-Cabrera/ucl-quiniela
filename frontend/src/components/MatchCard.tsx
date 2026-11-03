import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Pencil } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import type { Match, Prediction } from "@/types";
import { Badge, StatusDot, PointsChip, TeamLogo } from "@/components/ui";
import { FirstGoalLine } from "@/components/FirstGoalLine";
import { WinProbabilityBar } from "@/components/WinProbabilityBar";
import { clsx } from "clsx";

interface MatchCardProps {
  match: Match;
  prediction?: Prediction;
  onPredict?: (match: Match) => void;
  /** Reservar el hueco de la barra de probabilidad / del primer gol real aunque este
   *  partido no los tenga: la cuadrícula lo pide cuando otra tarjeta del mismo día sí
   *  los muestra, para que todas mantengan cada bloque al mismo nivel. */
  reserveProbability?: boolean;
  reserveFirstGoal?: boolean;
}

// Nombre de equipo: dos líneas reservadas (y como máximo) para que la fila de equipos
// mida lo mismo en todas las tarjetas, tenga el nombre una o dos líneas.
const TEAM_NAME_CLS = "text-sm text-center font-medium leading-tight min-h-[2.25rem] line-clamp-2";

// Pausas que la API marca con su propio status.short: en ellas el minuto se queda fijo
// (45 en el descanso, 105 en el de la prórroga, 120 en los penales), así que se muestra
// la etiqueta en vez del minuto; al reanudarse (2H, ET) vuelve el minuto.
const LIVE_PAUSE_KEYS: Record<string, string> = {
  HT:   "status.halfTime",
  BT:   "status.extraTimeBreak",
  P:    "status.penaltyShootout",
  SUSP: "status.suspended",
  INT:  "status.interrupted",
};

/** Reloj de un partido en vivo: la etiqueta de la pausa si la hay, si no el minuto
 *  ("67′", "90+3′"); null si no hay nada que mostrar (se enseña la fecha). */
function liveClock(match: Match, t: TFunction): string | null {
  if (match.status !== "live") return null;
  const pauseKey = match.api_status ? LIVE_PAUSE_KEYS[match.api_status] : undefined;
  if (pauseKey) return t(pauseKey);
  if (match.elapsed == null) return null;
  return `${match.elapsed}${match.elapsed_extra ? `+${match.elapsed_extra}` : ""}′`;
}

export function MatchCard({ match, prediction, onPredict, reserveProbability, reserveFirstGoal }: MatchCardProps) {
  const { t } = useTranslation();
  const isFinished  = match.status === "finished";
  const canPredict  = match.predictable;   // plazo de jornada + prórroga (backend)
  const hasExact    = prediction &&
    prediction.predicted_home === match.home_score &&
    prediction.predicted_away === match.away_score;
  const clock       = liveClock(match, t);
  // Primer gol real: el goleador en cuanto la API lo atribuye; mientras tanto (la API
  // publica el gol y lo atribuye minutos después) al menos el equipo que lo marcó.
  const firstGoal   = match.first_goal_player ?? match.first_goal_team;

  return (
    <div
      className={clsx(
        // h-full + flex-col: la grilla estira las tarjetas a igual altura y el pie
        // (botón) se ancla abajo con mt-auto → los botones quedan siempre alineados.
        "card p-4 transition-all duration-200 group h-full flex flex-col",
        prediction && "border-ucl-gold/20",
        match.status === "live" && "border-red-500/30 shadow-[0_0_20px_rgba(239,68,68,0.08)]"
      )}
    >
      {/* Header: fase + status */}
      <div className="flex items-center justify-between mb-4">
        <Badge variant={match.phase === "league" ? "blue" : "gold"}>
          {t(`phase.${match.phase}`)}
        </Badge>
        <StatusDot status={match.status} />
      </div>

      {/* Teams + Score. mb-4 = gap mínimo fijo hasta el pie; el pie usa mt-auto para
          absorber el espacio extra de la fila y anclarse abajo sin quedar pegado. */}
      <div className="flex items-center gap-3 mb-4">
        {/* Home */}
        <div className="flex-1 flex flex-col items-center gap-2">
          <TeamLogo src={match.home_team_logo} alt={match.home_team} className="w-10 h-10 text-lg" />
          <span className={TEAM_NAME_CLS} title={match.home_team}>{match.home_team}</span>
        </div>

        {/* Score / VS */}
        <div className="flex flex-col items-center gap-1 min-w-[64px]">
          {isFinished || match.status === "live" ? (
            <span className="font-display text-3xl text-ucl-white tracking-widest">
              {match.home_score} - {match.away_score}
            </span>
          ) : (
            <span className="font-display text-xl text-ucl-silver/50">VS</span>
          )}
          {/* Penales (eliminatoria definida en la tanda) */}
          {match.penalty_home != null && match.penalty_away != null && (
            <span className="text-xs text-ucl-gold font-mono">
              {t("matchCard.penalties", { home: match.penalty_home, away: match.penalty_away })}
            </span>
          )}
          {/* Reloj en vivo: minuto ("45+2", "90+3"; la prórroga sigue 91′…120′) o la
              etiqueta de la pausa (Descanso, Penales…); fuera de juego, la fecha. */}
          {clock ? (
            <span className="text-xs text-red-400 font-mono font-semibold">{clock}</span>
          ) : (
            <span className="text-xs text-ucl-silver/50 font-mono">
              {format(new Date(match.match_date), "d MMM · HH:mm", { locale: es })}
            </span>
          )}
        </div>

        {/* Away */}
        <div className="flex-1 flex flex-col items-center gap-2">
          <TeamLogo src={match.away_team_logo} alt={match.away_team} className="w-10 h-10 text-lg" />
          <span className={TEAM_NAME_CLS} title={match.away_team}>{match.away_team}</span>
        </div>
      </div>

      {/* Probabilidad de victoria pre-partido (solo el próximo partido de cada equipo). */}
      <WinProbabilityBar match={match} placeholder={reserveProbability} />

      {/* Primer goleador real: en cuanto se conoce (en vivo o finalizado), para todos,
          tengan o no pronóstico. Sin dato pero con `reserveFirstGoal`, el hueco se
          conserva invisible (p. ej. un 0-0 junto a partidos con gol). */}
      {(firstGoal || reserveFirstGoal) && (
        <div
          className={clsx("-mt-2 mb-4 flex items-center justify-center gap-1.5 text-xs", !firstGoal && "invisible")}
          aria-hidden={!firstGoal}
        >
          <span className="text-ucl-silver/50">⚽ {t("common.firstGoalReal")}:</span>
          <span className="font-medium text-ucl-white">{firstGoal ?? "—"}</span>
        </div>
      )}

      {/* Prediction row */}
      {prediction ? (
        <div className="mt-auto pt-3 border-t border-ucl-blue/30 flex items-center justify-between">
          <div className="text-sm">
            <div className="flex items-center gap-2">
              <span className="text-ucl-silver/60 text-xs">{t("matchCard.yourPrediction")}</span>
              <span className={clsx("font-mono font-bold", hasExact ? "text-ucl-gold" : "text-ucl-white")}>
                {prediction.predicted_home} - {prediction.predicted_away}
              </span>
              {hasExact && <span className="text-xs text-ucl-gold">{t("matchCard.exact")}</span>}
            </div>
            <FirstGoalLine prediction={prediction} match={match} showReal={false} />
          </div>
          <div className="flex items-center gap-2">
            {prediction.is_calculated && <PointsChip points={prediction.points_earned} />}
            {canPredict && onPredict && (
              <button
                onClick={() => onPredict(match)}
                className="text-ucl-silver/40 hover:text-ucl-gold transition-colors p-1"
                title={t("matchCard.editPrediction")}
              >
                <Pencil size={14} />
              </button>
            )}
          </div>
        </div>
      ) : canPredict && onPredict ? (
        <div className="mt-auto pt-3 border-t border-ucl-blue/30">
          <button
            onClick={() => onPredict(match)}
            className="btn-primary w-full text-sm py-2"
          >
            {t("matchCard.predict")}
          </button>
        </div>
      ) : null}
    </div>
  );
}
