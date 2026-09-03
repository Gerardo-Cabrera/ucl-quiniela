import { useState } from "react";
import { Check, Search, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";
import type { Player } from "@/types";
import { groupSquad } from "@/lib/players";
import { TeamLogo } from "@/components/ui";

interface TeamRef {
  name: string;
  logo: string | null;
}

interface Props {
  players: Player[];
  teams: [TeamRef, TeamRef];   // local, visitante
  value: number | null;
  onChange: (id: number | null) => void;
}

/** Selector visual del primer goleador: pestañas de equipo (con escudo), filtro
 *  por nombre y cuadrícula de FOTOS agrupada por posición. Reconocer una cara es
 *  más fácil que un apellido que quizá no se conoce, y los botones grandes van
 *  bien en móvil. Con filtro se busca en ambos equipos; sin él, solo en el activo. */
export function PlayerPicker({ players, teams, value, onChange }: Props) {
  const { t } = useTranslation();
  const [team, setTeam]   = useState(teams[0].name);
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();
  const selected = players.find((p) => p.api_player_id === value);
  const pool   = q ? players.filter((p) => p.name.toLowerCase().includes(q)) : players;
  const squads = groupSquad(pool, q ? teams.map((x) => x.name) : [team]);

  return (
    <div className="space-y-3">
      {selected && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-ucl-silver/60">{t("predictionModal.picked")}</span>
          <span className="text-ucl-gold font-medium truncate">{selected.name}</span>
          <button
            type="button"
            onClick={() => onChange(null)}
            aria-label={t("common.close")}
            className="text-ucl-silver/50 hover:text-red-400 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Pestañas de equipo */}
      <div className="grid grid-cols-2 gap-2">
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
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ucl-silver/40" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("predictionModal.filterPlaceholder")}
          className="input-base w-full pl-9 py-2 text-sm"
        />
      </div>

      {/* Cuadrícula de fotos por posición */}
      <div className="max-h-64 overflow-y-auto pr-1 space-y-3">
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
                    return (
                      <button
                        type="button"
                        key={p.api_player_id}
                        aria-pressed={isSelected}
                        onClick={() => onChange(isSelected ? null : p.api_player_id)}
                        className={clsx(
                          "flex flex-col items-center gap-1 rounded-lg p-1.5 min-w-0 transition-colors",
                          isSelected ? "bg-ucl-gold/15" : "hover:bg-ucl-blue/30",
                        )}
                      >
                        <span className="relative">
                          <span className={clsx(
                            "block w-12 h-12 rounded-full overflow-hidden border-2 bg-ucl-navy",
                            isSelected ? "border-ucl-gold" : "border-ucl-blue/50",
                          )}>
                            {p.photo
                              ? <img src={p.photo} alt="" loading="lazy" className="w-full h-full object-cover" />
                              : <span className="w-full h-full flex items-center justify-center">⚽</span>}
                          </span>
                          {isSelected && (
                            <span className="absolute -bottom-0.5 -right-0.5 rounded-full bg-ucl-gold text-ucl-navy p-0.5">
                              <Check size={10} />
                            </span>
                          )}
                        </span>
                        <span className={clsx(
                          "w-full text-[11px] leading-tight text-center truncate",
                          isSelected ? "text-ucl-gold font-medium" : "text-ucl-silver",
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
