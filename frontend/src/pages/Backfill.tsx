import { useState } from "react";
import { Navigate } from "react-router-dom";
import { format } from "date-fns";
import { Plus, Trash2, Upload } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/store/authStore";
import { useBackfill, useLeaderboard, useMatches, useMatchPlayers } from "@/hooks";
import { Card } from "@/components/ui";
import { PredictionsByDay } from "@/components/PredictionCard";
import { apiErrorMessage } from "@/lib/apiError";
import { formatDayHeading, groupByDay } from "@/lib/date";
import { groupSquad } from "@/lib/players";
import { MATCH_PHASES, type Match, type MatchPhase } from "@/types";

/** Una fila = un pronóstico a cargar. `""` = sin elegir (partido o goleador). */
interface Row {
  id: number;
  match_id: number | "";
  predicted_home: number;
  predicted_away: number;
  first_goal_player_id: number | "";
}

let rowSeq = 0;
const emptyRow = (): Row => ({
  id: ++rowSeq, match_id: "", predicted_home: 0, predicted_away: 0, first_goal_player_id: "",
});
const clampScore = (v: string) => Math.max(0, Math.min(20, Number(v) || 0));

// Input de gol: ancho fijo y centrado, sin las flechas del number (tapaban el dígito).
const SCORE_CLS =
  "input-base w-16 text-center px-1 font-mono text-lg " +
  "[appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none";

/** Fila del formulario: partido de la fase (agrupados por día), marcador y, con goles,
 *  el primer goleador elegido de las plantillas de ESE partido (se envía el id: sin
 *  ambigüedad de nombres). Un 0-0 no lleva goleador: el selector se desactiva y se limpia. */
function BackfillRow({ row, matches, onChange, onRemove, removable }: {
  row: Row;
  matches: Match[];
  onChange: (next: Row) => void;
  onRemove: () => void;
  removable: boolean;
}) {
  const { t } = useTranslation();
  const match = matches.find((m) => m.id === row.match_id);
  const { data: players = [] } = useMatchPlayers(row.match_id || 0);
  const goalless = row.predicted_home + row.predicted_away === 0;
  const squads = match ? groupSquad(players, [match.home_team, match.away_team]) : [];

  const setScore = (field: "predicted_home" | "predicted_away", value: string) => {
    const next = { ...row, [field]: clampScore(value) };
    if (next.predicted_home + next.predicted_away === 0) next.first_goal_player_id = "";
    onChange(next);
  };

  return (
    <div className="border border-ucl-blue/30 rounded-lg p-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={row.match_id}
          onChange={(e) => onChange({ ...row, match_id: e.target.value ? Number(e.target.value) : "", first_goal_player_id: "" })}
          className="input-base flex-1 min-w-[220px]"
          aria-label={t("backfill.selectMatch")}
        >
          <option value="">{t("backfill.selectMatch")}</option>
          {groupByDay(matches, (m) => m.match_date).map((group) => (
            <optgroup key={group.day} label={formatDayHeading(group.date)}>
              {group.items.map((m) => (
                <option key={m.id} value={m.id}>
                  {format(new Date(m.match_date), "HH:mm")} · {m.home_team} {t("common.vs")} {m.away_team}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        <input
          type="number" min={0} max={20} value={row.predicted_home} aria-label={t("backfill.home")}
          onChange={(e) => setScore("predicted_home", e.target.value)} className={SCORE_CLS}
        />
        <span className="text-ucl-silver/40">-</span>
        <input
          type="number" min={0} max={20} value={row.predicted_away} aria-label={t("backfill.away")}
          onChange={(e) => setScore("predicted_away", e.target.value)} className={SCORE_CLS}
        />
        {removable && (
          <button
            type="button" onClick={onRemove} title={t("backfill.removeRow")} aria-label={t("backfill.removeRow")}
            className="text-ucl-silver/40 hover:text-red-400 transition-colors p-1"
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
      <select
        value={row.first_goal_player_id}
        disabled={!match || goalless}
        onChange={(e) => onChange({ ...row, first_goal_player_id: e.target.value ? Number(e.target.value) : "" })}
        className="input-base w-full text-sm disabled:opacity-50"
        aria-label={t("backfill.scorer")}
      >
        <option value="">{goalless ? t("backfill.scorerGoalless") : t("backfill.noScorer")}</option>
        {squads.map((squad) => (
          <optgroup key={squad.team} label={squad.team}>
            {squad.positions.flatMap((g) => g.players).map((p) => (
              <option key={p.api_player_id} value={p.api_player_id}>{p.name}</option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}

/** Vista solo de admin: carga (o corrige) los pronósticos de un participante hechos
 *  fuera de la app (papel, WhatsApp). Participante de la Tabla General (cuentas activas),
 *  fase y partido reales; el backend no valida el plazo y, si el partido ya terminó,
 *  puntúa al instante. Lo cargado se muestra con las tarjetas de Mis Pronósticos. */
export default function BackfillPage() {
  const { t } = useTranslation();
  const isAdmin = useAuthStore((s) => s.user?.is_admin ?? false);
  const { data: leaderboard } = useLeaderboard();
  const { data: matches } = useMatches();
  const { mutate: backfill, isPending, data: result, error, reset } = useBackfill();
  const [teamName, setTeamName] = useState("");
  const [phase, setPhase] = useState<MatchPhase>("league");
  const [rows, setRows] = useState<Row[]>([emptyRow()]);

  if (!isAdmin) return <Navigate to="/" replace />;

  const participants = (leaderboard ?? []).map((e) => e.team_name).sort((a, b) => a.localeCompare(b));
  const phaseMatches = (matches ?? []).filter((m) => m.phase === phase);
  const validRows = rows.filter((r) => r.match_id !== "");
  const canSubmit = teamName !== "" && validRows.length > 0 && !isPending;

  // Al cambiar de fase los partidos elegidos ya no aplican: se reinician las filas.
  const changePhase = (p: MatchPhase) => { setPhase(p); setRows([emptyRow()]); };
  const setRow = (i: number, next: Row) => setRows((rs) => rs.map((r, j) => (j === i ? next : r)));

  const submit = () => {
    reset();
    backfill({
      team_name: teamName,
      predictions: validRows.map((r) => ({
        match_id: r.match_id as number,
        predicted_home: r.predicted_home,
        predicted_away: r.predicted_away,
        first_goal_player_id: r.first_goal_player_id === "" ? undefined : r.first_goal_player_id,
      })),
    });
  };

  return (
    <div className="space-y-6 animate-in">
      <div>
        <h1 className="font-display text-4xl text-ucl-gold">{t("backfill.title")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("backfill.subtitle")}</p>
        <p className="text-ucl-silver/50 text-xs mt-2">{t("backfill.hint")}</p>
      </div>

      <Card className="space-y-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("backfill.participant")}</label>
            <select value={teamName} onChange={(e) => setTeamName(e.target.value)} className="input-base w-full">
              <option value="">{t("backfill.selectParticipant")}</option>
              {participants.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-[180px]">
            <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{t("backfill.phase")}</label>
            <select value={phase} onChange={(e) => changePhase(e.target.value as MatchPhase)} className="input-base w-full">
              {MATCH_PHASES.map((p) => <option key={p} value={p}>{t(`phase.${p}`)}</option>)}
            </select>
          </div>
        </div>

        <div className="space-y-3">
          {rows.map((row, i) => (
            <BackfillRow
              key={row.id}
              row={row}
              matches={phaseMatches}
              onChange={(next) => setRow(i, next)}
              onRemove={() => setRows((rs) => rs.filter((_, j) => j !== i))}
              removable={rows.length > 1}
            />
          ))}
        </div>

        <div className="flex items-center justify-between gap-3">
          <button
            type="button" onClick={() => setRows((rs) => [...rs, emptyRow()])}
            className="inline-flex items-center gap-1.5 text-sm text-ucl-silver hover:text-ucl-gold transition-colors"
          >
            <Plus size={16} /> {t("backfill.addRow")}
          </button>
          <button
            type="button" onClick={submit} disabled={!canSubmit}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Upload size={16} /> {isPending ? t("backfill.loading") : t("backfill.submit")}
          </button>
        </div>

        {error && (
          <p role="alert" className="text-red-400 text-sm">{apiErrorMessage(error, t("backfill.error"))}</p>
        )}
      </Card>

      {result && result.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-2xl text-ucl-gold">{t("backfill.loaded", { count: result.length })}</h2>
          <PredictionsByDay predictions={result} />
        </section>
      )}
    </div>
  );
}
