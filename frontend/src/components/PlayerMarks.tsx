import { Ban, CircleHelp, Cross, Star, UserX, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { clsx } from "clsx";
import type { Player, PlayerAvailability } from "@/types";

/** Marcas que ayudan a elegir un jugador (las calcula el backend con los datos de los
 *  partidos ya jugados y las bajas de API-Football): goles en esta Champions y máximo
 *  goleador de su equipo, y si es baja para el partido (sancionado, lesionado, duda o
 *  no disponible). Un solo sitio para el selector de primer goleador y el de MVP /
 *  máximo goleador: mismos colores, mismos iconos, misma leyenda. */

// Baja o duda para ESE partido: icono, color de la marca y del texto.
const AVAILABILITY: Record<PlayerAvailability, { icon: LucideIcon; badge: string; text: string }> = {
  injured:     { icon: Cross,      badge: "bg-red-500 text-white",        text: "text-red-300" },
  suspended:   { icon: Ban,        badge: "bg-red-500 text-white",        text: "text-red-300" },
  unavailable: { icon: UserX,      badge: "bg-ucl-silver text-ucl-navy",  text: "text-ucl-silver/70" },
  doubtful:    { icon: CircleHelp, badge: "bg-amber-400 text-ucl-navy",   text: "text-amber-300" },
};

const LEGEND_ORDER: PlayerAvailability[] = ["suspended", "injured", "doubtful", "unavailable"];

/** ¿Se lo pierde? (lesionado, sancionado o fuera de la lista; la duda puede jugar). */
export const isOut = (p: Player) => !!p.availability && p.availability !== "doubtful";

export const availabilityTextClass = (a: PlayerAvailability) => AVAILABILITY[a].text;

/** Goles en esta Champions. Dorado con estrella = máximo goleador de su equipo. */
export function GoalsBadge({ goals, top, className }: { goals: number; top: boolean; className?: string }) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-0.5 h-[17px] px-1 rounded-full text-[10px] leading-none font-bold font-mono whitespace-nowrap",
      top ? "bg-ucl-gold text-ucl-navy" : "bg-ucl-navy text-ucl-white border border-ucl-silver/40",
      className,
    )}>
      {top ? <Star size={9} fill="currentColor" strokeWidth={0} /> : <span className="text-[8px]">⚽</span>}
      {goals}
    </span>
  );
}

/** Baja o duda: círculo de color con su icono. */
export function AvailabilityBadge({ status, className }: { status: PlayerAvailability; className?: string }) {
  const { icon: Icon, badge } = AVAILABILITY[status];
  return (
    <span className={clsx("inline-flex items-center justify-center w-[17px] h-[17px] rounded-full", badge, className)}>
      <Icon size={11} strokeWidth={2.5} />
    </span>
  );
}

/** Estado de baja en texto: "Sancionado (acumulación de amarillas)", "Lesionado (lesión
 *  de rodilla)". El motivo llega en el vocabulario de API-Football (inglés) y se traduce
 *  con `absenceReason.*`; uno que no esté en la tabla se muestra tal cual. */
export function availabilityLabel(p: Player, t: TFunction): string | null {
  if (!p.availability) return null;
  const label = t(`playerMarks.${p.availability}`);
  const raw = p.availability_reason?.trim();
  if (!raw) return label;
  return `${label} (${t(`absenceReason.${raw.toLowerCase()}`, { defaultValue: raw })})`;
}

/** Todas las marcas del jugador en una línea (tooltip en escritorio y texto accesible). */
export function playerNotes(p: Player, t: TFunction): string {
  const notes = [
    p.team_top_scorer ? t("playerMarks.topScorer") : null,
    p.goals ? t("playerMarks.goals", { count: p.goals }) : null,
    availabilityLabel(p, t),
    p.availability_manual ? t("playerMarks.manual") : null,
  ].filter(Boolean);
  return [p.name, ...notes].join(" · ");
}

/** Leyenda de las marcas PRESENTES en `players` (en móvil no hay tooltip: los iconos
 *  deben explicarse solos). Sin ninguna marca no ocupa espacio. */
export function PlayerLegend({ players, className }: { players: Player[]; className?: string }) {
  const { t } = useTranslation();
  const topScorer = players.some((p) => p.team_top_scorer);
  const scorers   = players.some((p) => (p.goals ?? 0) > 0 && !p.team_top_scorer);
  const statuses  = LEGEND_ORDER.filter((s) => players.some((p) => p.availability === s));
  if (!topScorer && !scorers && statuses.length === 0) return null;

  const item = (key: string, mark: React.ReactNode, label: string) => (
    <span key={key} className="inline-flex items-center gap-1">{mark}{label}</span>
  );
  return (
    <div className={clsx("flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[11px] text-ucl-silver/70", className)}>
      {topScorer && item("top", <GoalsBadge goals={3} top />, t("playerMarks.legendTopScorer"))}
      {scorers && item("goals", <GoalsBadge goals={1} top={false} />, t("playerMarks.legendGoals"))}
      {statuses.map((s) => item(s, <AvailabilityBadge status={s} />, t(`playerMarks.${s}`)))}
    </div>
  );
}
