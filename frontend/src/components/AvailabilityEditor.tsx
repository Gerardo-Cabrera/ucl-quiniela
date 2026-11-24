import { useState } from "react";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { ManualAvailability, Player } from "@/types";
import { useClearPlayerAvailability, useSetPlayerAvailability } from "@/hooks";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";
import { clsx } from "clsx";

const STATUSES: ManualAvailability[] = ["available", "suspended", "injured", "doubtful", "unavailable"];

/** Corrección manual del estado de un jugador para un partido (solo admin). El proveedor
 *  tarda en registrar las lesiones recientes: aquí el admin anota lo que ya se sabe (o
 *  desmiente una baja con "Disponible"). Manda sobre los datos automáticos y el job de
 *  bajas no la pisa; "Quitar corrección" devuelve al jugador a lo automático. */
export function AvailabilityEditor({ matchId, player, onClose }: {
  matchId: number;
  player: Player;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<ManualAvailability>(player.availability ?? "available");
  // El motivo solo se precarga si ya era una corrección manual: el de la API viene en inglés.
  const [reason, setReason] = useState(player.availability_manual ? (player.availability_reason ?? "") : "");
  const save = useSetPlayerAvailability(matchId);
  const clear = useClearPlayerAvailability(matchId);
  const busy = save.isPending || clear.isPending;
  const error = save.error ?? clear.error;

  return (
    <div className="mb-6 rounded-lg border border-ucl-gold/30 bg-ucl-navy/60 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm min-w-0 truncate">
          <span className="text-ucl-silver/60">{t("playerMarks.editTitle")} </span>
          <span className="text-ucl-gold font-medium">{player.name}</span>
        </p>
        <button type="button" onClick={onClose} aria-label={t("common.close")}
                className="text-ucl-silver/50 hover:text-ucl-white transition-colors shrink-0">
          <X size={14} />
        </button>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map((s) => (
          <button
            type="button"
            key={s}
            aria-pressed={s === status}
            onClick={() => setStatus(s)}
            className={clsx(
              "px-2 py-1 rounded-full text-[11px] font-mono transition-colors",
              s === status
                ? "bg-ucl-blue text-ucl-white font-bold"
                : "border border-ucl-blue/50 text-ucl-silver hover:border-ucl-silver",
            )}
          >
            {t(`playerMarks.${s}`)}
          </button>
        ))}
      </div>

      {status !== "available" && (
        <input
          type="text"
          value={reason}
          maxLength={80}
          onChange={(e) => setReason(e.target.value)}
          placeholder={t("playerMarks.editReason")}
          aria-label={t("playerMarks.editReason")}
          className="input-base w-full py-1.5 text-sm"
        />
      )}

      <div className="flex items-center justify-between gap-2">
        {player.availability_manual ? (
          <button
            type="button" disabled={busy}
            onClick={() => clear.mutate(player.api_player_id, { onSuccess: onClose })}
            className="text-xs text-ucl-silver/70 hover:text-red-400 transition-colors disabled:opacity-40"
          >
            {t("playerMarks.editClear")}
          </button>
        ) : <span />}
        <button
          type="button" disabled={busy}
          onClick={() => save.mutate(
            { playerId: player.api_player_id, status, reason: status === "available" ? null : reason.trim() || null },
            { onSuccess: onClose },
          )}
          className="btn-primary text-sm px-4 py-1.5 flex items-center gap-2"
        >
          {busy && <Spinner size="sm" />} {t("playerMarks.editSave")}
        </button>
      </div>

      {error && <p role="alert" className="text-xs text-red-400">{apiErrorMessage(error, t("playerMarks.editError"))}</p>}
    </div>
  );
}
