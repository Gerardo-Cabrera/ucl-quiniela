import { useState } from "react";
import { Check, Pencil, Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import type { Player } from "@/types";
import { groupSquad } from "@/lib/players";
import { TeamLogo } from "@/components/ui";
import { useAuthStore } from "@/store/authStore";
import { AvailabilityEditor } from "@/components/AvailabilityEditor";
import {
  AvailabilityBadge, GoalsBadge, PlayerLegend,
  availabilityLabel, availabilityTextClass, isOut, playerNotes,
} from "@/components/PlayerMarks";

interface TeamRef {
  name: string;
  logo: string | null;
}

interface Props {
  players: Player[];
  teams: [TeamRef, TeamRef];   // local, visitante
  /** Goleador elegido y cómo cambiarlo. Se omiten en el modo `editOnly`. */
  value?: number | null;
  onChange?: (id: number | null) => void;
  /** Partido de estas plantillas: con él, el admin puede corregir a mano la disponibilidad. */
  matchId?: number;
  /** Solo corregir bajas (modal de bajas del admin): no se elige goleador y tocar a un
   *  jugador abre siempre su estado. */
  editOnly?: boolean;
}

/** Selector visual del primer goleador: pestañas de equipo (con escudo), filtro
 *  por nombre y cuadrícula de FOTOS agrupada por posición. Reconocer una cara es
 *  más fácil que un apellido que quizá no se conoce, y los botones grandes van
 *  bien en móvil. Con filtro se busca en ambos equipos; sin él, solo en el activo.
 *
 *  Cada foto lleva en sus esquinas lo que conviene saber antes de elegir (ver
 *  PlayerMarks): arriba a la derecha los goles (dorado con estrella = máximo goleador
 *  de su equipo) y abajo a la izquierda si es baja para este partido (sancionado,
 *  lesionado, duda o no disponible; quien se lo pierde sale atenuado). Son marcas
 *  superpuestas: ninguna celda cambia de tamaño. Una baja se puede elegir igualmente
 *  (el dato puede ir con retraso); al hacerlo, el aviso queda junto al nombre.
 *
 *  Solo el admin ve además «Corregir bajas»: con ese modo activo, tocar a un jugador no
 *  lo elige como goleador sino que abre su estado para corregirlo (AvailabilityEditor).
 *  Con `editOnly` (modal de bajas, abierto desde la tarjeta del partido) ese modo es el
 *  único: no hay goleador que elegir. */
export function PlayerPicker({ players, teams, value = null, onChange, matchId, editOnly = false }: Props) {
  const { t } = useTranslation();
  const isAdmin = useAuthStore((s) => s.user?.is_admin ?? false);
  const canEdit = isAdmin && matchId != null;
  const [team, setTeam]   = useState(teams[0].name);
  const [query, setQuery] = useState("");
  const [editToggle, setEditToggle] = useState(false);        // modo «Corregir bajas» (admin)
  const editing = editOnly || editToggle;
  const [targetId, setTargetId] = useState<number | null>(null);
  const target = players.find((p) => p.api_player_id === targetId);
  const q = query.trim().toLowerCase();
  const selected = players.find((p) => p.api_player_id === value);
  const pool   = q ? players.filter((p) => p.name.toLowerCase().includes(q)) : players;
  const squads = groupSquad(pool, q ? teams.map((x) => x.name) : [team]);

  // `contents`: los bloques del selector son hijos directos de la columna flex del modal.
  // Solo la cuadrícula puede ceder altura (hasta su mínimo, con desplazamiento propio);
  // el resto conserva la suya. Mientras el admin corrige a un jugador, su editor ocupa el
  // sitio de la cuadrícula y de la leyenda.
  const correcting = canEdit && editing && !!target;
  return (
    <div className="contents">
      {selected && (
        <div className="mb-3 flex items-center gap-2 text-sm">
          <span className="text-ucl-silver/60">{t("predictionModal.picked")}</span>
          <span className="text-ucl-gold font-medium truncate">{selected.name}</span>
          <button
            type="button"
            onClick={() => onChange?.(null)}
            aria-label={t("common.close")}
            className="text-ucl-silver/50 hover:text-red-400 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      )}
      {/* Elegir a una baja no se impide, pero se avisa (en móvil no hay tooltip). */}
      {selected?.availability && (
        <p role="status" className={clsx("-mt-2 mb-3 text-xs", availabilityTextClass(selected.availability))}>
          {t(isOut(selected) ? "playerMarks.pickedWarningOut" : "playerMarks.pickedWarningDoubt",
             { status: availabilityLabel(selected, t) })}
        </p>
      )}

      {/* Pestañas de equipo */}
      <div className="mb-3 grid grid-cols-2 gap-2">
        {teams.map((tm) => (
          <button
            type="button"
            key={tm.name}
            onClick={() => setTeam(tm.name)}
            className={clsx(
              "flex items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors min-w-0",
              team === tm.name && !q
                ? "border-ucl-gold bg-ucl-gold/10 text-ucl-gold"
                : "border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold/60",
            )}
          >
            <TeamLogo src={tm.logo} className="w-5 h-5" />
            <span className="truncate">{tm.name}</span>
          </button>
        ))}
      </div>

      {/* Filtro por nombre (opcional) */}
      <div className="mb-3 relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ucl-silver/40" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("predictionModal.filterPlaceholder")}
          className="input-base w-full pl-9 py-2 text-sm"
        />
      </div>

      {!correcting && <PlayerLegend players={players} className="mb-3" />}

      {canEdit && (
        <div className="mb-3 flex items-center gap-2">
          {!editOnly && (
            <button
              type="button"
              aria-pressed={editing}
              onClick={() => { setEditToggle((on) => !on); setTargetId(null); }}
              className={clsx(
                "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-xs transition-colors",
                editing ? "border-ucl-gold bg-ucl-gold/10 text-ucl-gold"
                        : "border-ucl-blue/60 text-ucl-silver hover:border-ucl-gold/60",
              )}
            >
              <Pencil size={12} /> {t("playerMarks.editToggle")}
            </button>
          )}
          {editing && !target && <span className="min-w-0 text-[11px] leading-tight text-ucl-silver/60">{t("playerMarks.editHint")}</span>}
        </div>
      )}
      {correcting && (
        <AvailabilityEditor
          key={target.api_player_id}
          matchId={matchId}
          player={target}
          onClose={() => setTargetId(null)}
        />
      )}

      {/* Cuadrícula de fotos por posición */}
      <div className={clsx("mb-6 min-h-24 max-h-64 overflow-y-auto pr-1 space-y-3", correcting && "hidden")}>
        {squads.length === 0 && (
          <p className="text-sm text-ucl-silver/40 italic">{t("predictionModal.noMatches")}</p>
        )}
        {squads.map((sq) => (
          <div key={sq.team}>
            {q && <p className="font-display text-sm text-ucl-gold mb-1">{sq.team}</p>}
            {sq.positions.map((g) => (
              <div key={g.position} className="mb-2">
                <p className="text-[11px] font-mono uppercase tracking-wider text-ucl-silver/80 mb-1.5">
                  {t(`position.${g.position || "unknown"}`)}
                </p>
                <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
                  {g.players.map((p) => {
                    const isSelected = p.api_player_id === value;
                    const out = isOut(p);
                    const notes = playerNotes(p, t);
                    return (
                      <button
                        type="button"
                        key={p.api_player_id}
                        aria-pressed={isSelected}
                        aria-label={notes}
                        title={notes}
                        onClick={() => (editing && canEdit
                          ? setTargetId(p.api_player_id)
                          : onChange?.(isSelected ? null : p.api_player_id))}
                        className={clsx(
                          "flex flex-col items-center gap-1 rounded-lg p-1.5 min-w-0 transition-colors",
                          isSelected ? "bg-ucl-gold/15" : "hover:bg-ucl-blue/30",
                          editing && targetId === p.api_player_id && "ring-1 ring-ucl-gold",
                        )}
                      >
                        <span className="relative">
                          <span className={clsx(
                            "block w-12 h-12 rounded-full overflow-hidden border-2 bg-ucl-navy",
                            isSelected ? "border-ucl-gold" : "border-ucl-blue/50",
                          )}>
                            {p.photo
                              ? <img src={p.photo} alt="" loading="lazy" className={clsx("w-full h-full object-cover", out && "grayscale opacity-40")} />
                              : <span className={clsx("w-full h-full flex items-center justify-center", out && "opacity-40")}>⚽</span>}
                          </span>
                          {!!p.goals && <GoalsBadge goals={p.goals} top={!!p.team_top_scorer} className="absolute -top-1 -right-2" />}
                          {p.availability && <AvailabilityBadge status={p.availability} className="absolute -bottom-0.5 -left-1" />}
                          {isSelected && (
                            <span className="absolute -bottom-0.5 -right-0.5 rounded-full bg-ucl-gold text-ucl-navy p-0.5">
                              <Check size={10} />
                            </span>
                          )}
                        </span>
                        <span className={clsx(
                          "w-full text-[11px] leading-tight text-center truncate",
                          isSelected ? "text-ucl-gold font-medium"
                            : p.availability ? availabilityTextClass(p.availability)
                            : "text-ucl-silver",
                        )}>
                          {p.name}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
