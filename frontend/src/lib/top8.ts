import type { Top8Pick } from "@/types";

/** Aciertos de un Top 8 frente al real (mismo criterio que el scoring del backend):
 *  exactos (equipo en su posición), solo el equipo (en otra posición) y fuera. */
export function top8Hits(
  picks: Pick<Top8Pick, "position" | "team_name">[],
  actual: string[],
): { exact: number; team: number; miss: number } {
  let exact = 0;
  let team = 0;
  for (const p of picks) {
    if (actual[p.position - 1] === p.team_name) exact++;
    else if (actual.includes(p.team_name)) team++;
  }
  return { exact, team, miss: picks.length - exact - team };
}
