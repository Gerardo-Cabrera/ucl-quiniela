import type { Player } from "@/types";

/** Posiciones de API-Football en el orden en que se muestran (desconocidas al final). */
const POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Attacker"];
const rank = (position: string) => {
  const i = POSITION_ORDER.indexOf(position);
  return i === -1 ? POSITION_ORDER.length : i;
};

export interface PositionGroup {
  position: string;   // clave de API-Football ("" si desconocida); se traduce en la vista
  players: Player[];
}

export interface TeamSquad {
  team: string;
  positions: PositionGroup[];
}

/** Agrupa una plantilla por equipo (en el orden dado: local, visitante) y, dentro de
 *  cada equipo, por posición (portero → defensa → medio → delantero). Los jugadores
 *  conservan el orden de llegada (el backend ya los ordena por nombre). */
export function groupSquad(players: Player[], teams: string[]): TeamSquad[] {
  return teams
    .map((team) => {
      const byPosition = new Map<string, Player[]>();
      for (const p of players) {
        if (p.team_name !== team) continue;
        const key = p.position ?? "";
        byPosition.set(key, [...(byPosition.get(key) ?? []), p]);
      }
      const positions = [...byPosition.keys()]
        .sort((a, b) => rank(a) - rank(b))
        .map((position) => ({ position, players: byPosition.get(position)! }));
      return { team, positions };
    })
    .filter((squad) => squad.positions.length > 0);
}
