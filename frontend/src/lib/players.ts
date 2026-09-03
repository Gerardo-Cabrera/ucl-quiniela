import type { Player } from "@/types";

/** Posiciones de API-Football en el orden en que se muestran (desconocidas al final). */
const POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Attacker"];
const rank = (position: string) => {
  const i = POSITION_ORDER.indexOf(position);
  return i === -1 ? POSITION_ORDER.length : i;
};

export interface SquadGroup {
  team: string;
  position: string;   // clave de API-Football ("" si desconocida); se traduce en la vista
  players: Player[];
}

/** Agrupa una plantilla por equipo (en el orden dado: local, visitante) y, dentro de
 *  cada equipo, por posición (portero → defensa → medio → delantero). Los jugadores
 *  conservan el orden de llegada (el backend ya los ordena por nombre). */
export function groupSquad(players: Player[], teams: string[]): SquadGroup[] {
  const groups: SquadGroup[] = [];
  for (const team of teams) {
    const byPosition = new Map<string, Player[]>();
    for (const p of players) {
      if (p.team_name !== team) continue;
      const key = p.position ?? "";
      byPosition.set(key, [...(byPosition.get(key) ?? []), p]);
    }
    for (const position of [...byPosition.keys()].sort((a, b) => rank(a) - rank(b))) {
      groups.push({ team, position, players: byPosition.get(position)! });
    }
  }
  return groups;
}
