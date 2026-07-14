import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

/** Perfil del usuario logueado: equipo y email (solo lectura) y el alias
 *  (opcional) editable. Mismo estilo que la pantalla de acceso. */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, updateAlias } = useAuthStore();
  const navigate = useNavigate();
  const [alias, setAlias]     = useState(user?.alias ?? "");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError("");
    const trimmed = alias.trim();
    if (trimmed && trimmed.length < 3) { setError(t("auth.errAliasShort")); return; }
    setLoading(true);
    try {
      await updateAlias(trimmed || null);  // vacío → quita el alias
      toast.success(t("profile.saved"));
      navigate("/");
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const label = (text: string) => (
    <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{text}</label>
  );

  return (
    <div className="max-w-sm mx-auto">
      <div className="card border-ucl-gold/20 p-6">
        <h2 className="text-center text-ucl-gold font-display text-2xl tracking-wide mb-1">
          {t("profile.title")}
        </h2>
        <p className="text-center text-ucl-silver/70 text-sm mb-6">{t("profile.hint")}</p>

        <div className="space-y-4">
          <div>
            {label(t("auth.yourTeam"))}
            <input value={user?.team_name ?? ""} disabled className="input-base w-full opacity-60 cursor-not-allowed" />
          </div>
          <div>
            {label(t("auth.email"))}
            <input value={user?.email ?? ""} disabled className="input-base w-full opacity-60 cursor-not-allowed" />
          </div>
          <div>
            {label(t("auth.alias"))}
            <input
              type="text"
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              placeholder={t("auth.aliasPlaceholder")}
              className="input-base w-full"
              aria-label={t("auth.alias")}
            />
          </div>

          {error && (
            <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={submit}
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 mt-2"
          >
            {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("profile.save")}
          </button>
          <button
            onClick={() => navigate("/")}
            className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm"
          >
            {t("auth.changePassword.cancel")}
          </button>
        </div>
      </div>
    </div>
  );
}
