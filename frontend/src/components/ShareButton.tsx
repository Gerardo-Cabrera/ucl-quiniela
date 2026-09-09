import { Share2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { clsx } from "clsx";

/** Botón "Compartir": abre WhatsApp (u otra app) con `text` pre-cargado y la persona
 *  elige el grupo. Sin costo ni API externa (`wa.me`). Sin emojis en el texto
 *  (astral/4 bytes): WhatsApp los corrompe. `disabled` + `disabledTitle` explican
 *  por qué aún no se puede (p. ej. una jornada sin terminar). */
export function ShareButton({ text, ariaLabel, disabled = false, disabledTitle }: {
  text: string;
  ariaLabel: string;
  disabled?: boolean;
  disabledTitle?: string;
}) {
  const { t } = useTranslation();
  const share = () =>
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, "_blank", "noopener,noreferrer");
  return (
    <button
      onClick={share}
      disabled={disabled}
      aria-label={ariaLabel}
      title={disabled ? disabledTitle : ariaLabel}
      className={clsx(
        "flex items-center gap-1.5 text-xs font-medium border rounded-lg px-3 py-1.5 transition-colors shrink-0",
        disabled
          ? "text-ucl-silver/40 border-ucl-blue/30 cursor-not-allowed"
          : "text-ucl-silver hover:text-ucl-gold border-ucl-blue/50 hover:border-ucl-gold/50",
      )}
    >
      <Share2 size={14} /> {t("common.share")}
    </button>
  );
}
