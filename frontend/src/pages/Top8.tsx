import { useState, useEffect } from "react";
import {
  DndContext, closestCenter, PointerSensor,
  useSensor, useSensors, DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Search, Check, Award, Goal, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  useMyTop8, useSaveTop8, useTeamsConfig, useMatches,
  useMyTournament, useSaveTournament, useTournamentPlayers,
} from "@/hooks";
import { Spinner, PointsChip } from "@/components/ui";
import type { Player } from "@/types";
import { clsx } from "clsx";

interface PickItem {
  id: string;
  team_name: string;
}

type PlayerRef = { id: number; name: string };

/** Selector de un jugador con buscador (una sola selección). Bloqueado tras el
 *  cierre: muestra solo el nombre elegido y, si ya se calculó, sus puntos. */
function PlayerSelect({
  label, icon, players, selected, locked, points, onSelect,
}: {
  label: string;
  icon: React.ReactNode;
  players: Player[];
  selected: PlayerRef | null;
  locked: boolean;
  points: number | null;
  onSelect: (p: PlayerRef | null) => void;
}) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");

  const q = search.trim().toLowerCase();
  const matches = q
    ? players.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 40)
    : [];

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-ucl-gold">{icon}</span>
        <h3 className="font-display text-lg">{label}</h3>
        {points != null && <PointsChip points={points} />}
      </div>

      {selected ? (
        <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-ucl-blue/20 border border-ucl-blue/40">
          <span className="flex-1 text-sm font-medium truncate">{selected.name}</span>
          {!locked && (
            <button
              onClick={() => onSelect(null)}
              aria-label={t("common.close")}
              className="text-red-400/50 hover:text-red-400 transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>
      ) : locked ? (
        <p className="px-3 py-2.5 text-sm text-ucl-silver/40 italic">{t("tournament.noPick")}</p>
      ) : (
        <>
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ucl-silver/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("tournament.searchPlaceholder")}
              className="input-base w-full pl-9"
            />
          </div>
          {matches.length > 0 && (
            <div className="mt-2 space-y-1 max-h-56 overflow-y-auto pr-1">
              {matches.map((p) => (
                <button
                  key={p.api_player_id}
                  onClick={() => { onSelect({ id: p.api_player_id, name: p.name }); setSearch(""); }}
                  className="w-full px-3 py-2 rounded-lg text-sm text-left text-ucl-silver hover:bg-ucl-blue/30 hover:text-ucl-white transition-colors flex items-center justify-between gap-2"
                >
                  <span className="truncate">{p.name}</span>
                  <span className="text-xs text-ucl-silver/40 shrink-0">{p.team_name}</span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SortableItem({ item, index, locked }: { item: PickItem; index: number; locked: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: item.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={clsx(
        "flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-150",
        isDragging
          ? "bg-ucl-gold/20 border-ucl-gold/50 shadow-xl z-50"
          : "bg-ucl-blue/20 border-ucl-blue/40 hover:border-ucl-gold/30"
      )}
    >
      <span className="font-display text-2xl text-ucl-gold/70 w-8 text-center shrink-0">
        {index + 1}
      </span>
      <span className="flex-1 text-sm font-medium">{item.team_name}</span>
      {!locked && (
        <button {...attributes} {...listeners} className="text-ucl-silver/30 hover:text-ucl-silver cursor-grab active:cursor-grabbing">
          <GripVertical size={18} />
        </button>
      )}
    </div>
  );
}

export default function Top8Page() {
  const { t } = useTranslation();
  const { data: savedPicks, isLoading } = useMyTop8();
  const { mutate: save, isPending, isSuccess, reset } = useSaveTop8();
  const { data: teamsConfig } = useTeamsConfig();
  const { data: matches } = useMatches();
  const uclTeams = teamsConfig?.ucl_teams ?? [];

  const [picks, setPicks]   = useState<PickItem[]>([]);
  const [search, setSearch] = useState("");

  const sensors = useSensors(useSensor(PointerSensor));

  useEffect(() => {
    if (savedPicks?.length) {
      setPicks(
        // Copia antes de ordenar: .sort() muta en sitio y savedPicks es el array
        // cacheado por react-query (no se debe mutar).
        [...savedPicks]
          .sort((a, b) => a.position - b.position)
          .map((p) => ({ id: p.team_name, team_name: p.team_name }))
      );
    }
  }, [savedPicks]);

  // El Top 8 se fija al arrancar la temporada (primer partido) o tras calcularlo;
  // antes de eso es editable. El backend aplica la misma regla al guardar.
  const calculated    = savedPicks?.some((p) => p.is_calculated) ?? false;
  const seasonStarted = (matches ?? []).some((m) => Date.parse(m.match_date) <= Date.now());
  const locked        = calculated || seasonStarted;

  // ── Torneo: MVP y máximo goleador ──
  // Cierre distinto al Top 8: editables hasta que arranca la eliminatoria (primer
  // partido de fase ≠ league) o tras calcularse. El backend aplica la misma regla.
  const { data: tournament } = useMyTournament();
  const { mutate: saveTournament, isPending: tourSaving, isSuccess: tourSaved, reset: tourReset } = useSaveTournament();
  const tourCalculated  = tournament?.is_calculated ?? false;
  const knockoutStarted = (matches ?? []).some(
    (m) => m.phase !== "league" && Date.parse(m.match_date) <= Date.now(),
  );
  const tourLocked = tourCalculated || knockoutStarted;
  const { data: players } = useTournamentPlayers(!tourLocked);

  const [mvp, setMvp]       = useState<PlayerRef | null>(null);
  const [scorer, setScorer] = useState<PlayerRef | null>(null);

  useEffect(() => {
    setMvp(tournament?.mvp_player_id ? { id: tournament.mvp_player_id, name: tournament.mvp_player ?? "" } : null);
    setScorer(tournament?.top_scorer_player_id ? { id: tournament.top_scorer_player_id, name: tournament.top_scorer_player ?? "" } : null);
  }, [tournament]);

  const tourDirty =
    (mvp?.id ?? null)    !== (tournament?.mvp_player_id ?? null) ||
    (scorer?.id ?? null) !== (tournament?.top_scorer_player_id ?? null);

  const handleSaveTournament = () =>
    saveTournament({ mvp_player_id: mvp?.id ?? null, top_scorer_player_id: scorer?.id ?? null });

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      reset();
      setPicks((items) => {
        const from = items.findIndex((i) => i.id === active.id);
        const to   = items.findIndex((i) => i.id === over.id);
        return arrayMove(items, from, to);
      });
    }
  };

  const addTeam = (team: string) => {
    if (picks.length >= 8 || picks.find((p) => p.team_name === team)) return;
    reset();
    setPicks((prev) => [...prev, { id: team, team_name: team }]);
    setSearch("");
  };

  const removeTeam = (team: string) => {
    reset();
    setPicks((prev) => prev.filter((p) => p.team_name !== team));
  };

  const handleSave = () => {
    save(picks.map((p, i) => ({ position: i + 1, team_name: p.team_name })));
  };

  const filtered = uclTeams.filter(
    (team) =>
      team.toLowerCase().includes(search.toLowerCase()) &&
      !picks.find((p) => p.team_name === team)
  );

  const totalPoints = savedPicks?.reduce((s, p) => s + p.points_earned, 0) ?? 0;

  if (isLoading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-in">
      {/* Encabezado de la página: agrupa Top 8 + MVP/máximo goleador del torneo */}
      <div>
        <h1 className="font-display text-4xl text-ucl-gold">{t("tournament.pageTitle")}</h1>
        <p className="text-ucl-silver/60 text-sm mt-1">{t("tournament.pageSubtitle")}</p>
      </div>

      {/* Sección Top 8 */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-display text-2xl text-ucl-gold">{t("top8.title")}</h2>
          <p className="text-ucl-silver/60 text-sm mt-1">
            {t("top8.subtitle")}
          </p>
        </div>
        {totalPoints > 0 && (
          <div className="text-right">
            <p className="font-display text-4xl text-ucl-gold">{totalPoints}</p>
            <p className="text-xs text-ucl-silver/60 font-mono">{t("top8.ptsTop8")}</p>
          </div>
        )}
      </div>

      {/* Points info */}
      <div className="grid grid-cols-2 gap-3">
        <div className="card p-3 text-center">
          <p className="font-display text-3xl text-ucl-silver">{t("top8.pts3")}</p>
          <p className="text-xs text-ucl-silver/60 mt-1">{t("top8.pointsTeamOnly")}</p>
        </div>
        <div className="card p-3 text-center border-ucl-gold/20">
          <p className="font-display text-3xl text-ucl-gold">{t("top8.pts5")}</p>
          <p className="text-xs text-ucl-silver/60 mt-1">{t("top8.pointsExact")}</p>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: My picks (drag & drop) */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display text-xl">{t("top8.yourPrediction")}</h2>
            <span className={clsx(
              "font-mono text-sm",
              picks.length === 8 ? "text-ucl-gold" : "text-ucl-silver/60"
            )}>
              {picks.length}/8
            </span>
          </div>

          {picks.length === 0 ? (
            <div className="card p-8 text-center text-ucl-silver/50 text-sm border-dashed">
              {t("top8.selectHint")}
            </div>
          ) : (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={picks.map((p) => p.id)} strategy={verticalListSortingStrategy}>
                <div className="space-y-2">
                  {picks.map((item, i) => (
                    <div key={item.id} className="relative group">
                      <SortableItem item={item} index={i} locked={locked} />
                      {!locked && (
                        <button
                          onClick={() => removeTeam(item.team_name)}
                          className="absolute right-10 top-1/2 -translate-y-1/2 text-red-400/40 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          ✕
                        </button>
                      )}
                      {savedPicks?.find((p) => p.team_name === item.team_name && p.is_calculated) && (
                        <PointsChip
                          points={savedPicks.find((p) => p.team_name === item.team_name)?.points_earned ?? 0}
                        />
                      )}
                    </div>
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          )}

          {!locked && picks.length === 8 && (
            <button
              onClick={handleSave}
              disabled={isPending || isSuccess}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
            >
              {isPending ? <><Spinner size="sm" /> {t("top8.saving")}</> :
               isSuccess  ? <><Check size={16} /> {t("top8.saved")}</> :
               t("top8.save")}
            </button>
          )}

          {locked && (
            <div className="mt-4 bg-ucl-gold/10 border border-ucl-gold/20 rounded-lg px-4 py-3 text-sm text-ucl-gold/80">
              {calculated ? t("top8.locked") : t("top8.lockedSeason")}
            </div>
          )}
        </div>

        {/* Right: Team search */}
        <div>
          <h2 className="font-display text-xl mb-3">{t("top8.teamsTitle")}</h2>

          <div className="relative mb-3">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ucl-silver/40" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t("top8.searchPlaceholder")}
              className="input-base w-full pl-9"
            />
          </div>

          <div className="space-y-1.5 max-h-[420px] overflow-y-auto pr-1">
            {/* Los equipos ya elegidos salen de `filtered` (arriba), así que aquí
                solo aparecen los disponibles: al seleccionar uno, desaparece. */}
            {filtered.map((team) => {
              const full = picks.length >= 8 || locked;   // 8 elegidos o Top 8 bloqueado
              return (
                <button
                  key={team}
                  onClick={() => addTeam(team)}
                  disabled={full}
                  className={clsx(
                    "w-full px-4 py-2.5 rounded-lg text-sm text-left transition-all duration-150",
                    full
                      ? "opacity-30 cursor-not-allowed text-ucl-silver"
                      : "hover:bg-ucl-blue/30 hover:text-ucl-white text-ucl-silver"
                  )}
                >
                  {team}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Torneo: MVP y máximo goleador (cierre distinto: al arrancar la eliminatoria) */}
      <div className="pt-2 border-t border-ucl-blue/30">
        <div className="flex items-start justify-between mb-1">
          <h2 className="font-display text-2xl text-ucl-gold">{t("tournament.title")}</h2>
          {tourCalculated && (
            <div className="text-right">
              <p className="font-display text-3xl text-ucl-gold">
                {(tournament?.mvp_points ?? 0) + (tournament?.top_scorer_points ?? 0)}
              </p>
              <p className="text-xs text-ucl-silver/60 font-mono">{t("tournament.pts")}</p>
            </div>
          )}
        </div>
        <p className="text-ucl-silver/60 text-sm mb-4">{t("tournament.subtitle")}</p>

        <div className="grid sm:grid-cols-2 gap-4">
          <PlayerSelect
            label={t("tournament.mvp")}
            icon={<Award size={18} />}
            players={players ?? []}
            selected={mvp}
            locked={tourLocked}
            points={tourCalculated ? (tournament?.mvp_points ?? 0) : null}
            onSelect={(p) => { tourReset(); setMvp(p); }}
          />
          <PlayerSelect
            label={t("tournament.topScorer")}
            icon={<Goal size={18} />}
            players={players ?? []}
            selected={scorer}
            locked={tourLocked}
            points={tourCalculated ? (tournament?.top_scorer_points ?? 0) : null}
            onSelect={(p) => { tourReset(); setScorer(p); }}
          />
        </div>

        {!tourLocked && (
          <button
            onClick={handleSaveTournament}
            disabled={tourSaving || !tourDirty}
            className="btn-primary w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {tourSaving ? <><Spinner size="sm" /> {t("tournament.saving")}</> :
             tourSaved && !tourDirty ? <><Check size={16} /> {t("tournament.saved")}</> :
             t("tournament.save")}
          </button>
        )}

        {tourLocked && (
          <div className="mt-4 bg-ucl-gold/10 border border-ucl-gold/20 rounded-lg px-4 py-3 text-sm text-ucl-gold/80">
            {tourCalculated ? t("tournament.locked") : t("tournament.lockedKnockout")}
          </div>
        )}
      </div>
    </div>
  );
}
