import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Match } from "@/types";
import { useMatchPlayers } from "@/hooks";
import { PlayerPicker } from "@/components/PlayerPicker";
import { Spinner } from "@/components/ui";

/** Bajas de un partido, para el admin: las plantillas de los dos equipos con sus marcas
 *  y, al tocar a un jugador, su estado para corregirlo. Se abre desde la tarjeta del
 *  partido, sin pasar por el pronóstico: no depende de que el marcador tenga goles ni de
 *  que el plazo de la jornada siga abierto. Misma maquetación que el modal de pronóstico
 *  (columna flex en la que solo cede la cuadrícula de jugadores). */
export function AvailabilityModal({ match, onClose }: { match: Match; onClose: () => void }) {
  const { t } = useTranslation();
  const { data: players = [], isLoading } = useMatchPlayers(match.id);

  // Portal al body: escapa del ancestro con transform (`.animate-in`), que rompería el `fixed`.
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ucl-navy/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md max-h-[calc(100dvh-2rem)] overflow-y-auto flex flex-col card border-ucl-gold/25 p-6 shadow-2xl animate-in">
        <button onClick={onClose} aria-label={t("common.close")}
                className="absolute top-4 right-4 text-ucl-silver/60 hover:text-ucl-white transition-colors">
          <X size={20} />
        </button>
        <h2 className="font-display text-2xl text-ucl-gold mb-1 pr-8">{t("playerMarks.editModalTitle")}</h2>
        <p className="text-ucl-silver/60 text-sm mb-5">{match.home_team} vs {match.away_team}</p>

        {isLoading ? (
          <div className="mb-6 flex items-center gap-2 text-ucl-silver/50 text-sm">
            <Spinner size="sm" /> {t("predictionModal.loadingPlayers")}
          </div>
        ) : players.length === 0 ? (
          <p className="mb-6 text-ucl-silver/40 text-sm">{t("predictionModal.noSquads")}</p>
        ) : (
          <PlayerPicker
            players={players}
            teams={[
              { name: match.home_team, logo: match.home_team_logo },
              { name: match.away_team, logo: match.away_team_logo },
            ]}
            matchId={match.id}
            editOnly
          />
        )}
      </div>
    </div>,
    document.body,
  );
}
