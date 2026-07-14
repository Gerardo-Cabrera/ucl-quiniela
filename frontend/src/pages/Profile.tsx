import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

/** Perfil del usuario logueado. Un ÚNICO botón "Guardar" aplica lo que el usuario
 *  haya tocado: el alias (si lo cambió/agregó/quitó) y/o la contraseña (si llenó
 *  esos campos). Los campos de contraseña vacíos = no se cambia. */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, updateAlias, changePassword } = useAuthStore();
  const navigate = useNavigate();

  const [alias, setAlias]     = useState(user?.alias ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  const save = async () => {
    setError("");
    const normalizedAlias = alias.trim();
    const aliasChanged = normalizedAlias !== (user?.alias ?? "");
    const wantsPassword = Boolean(current || next || confirm);

    // Validaciones locales (el backend re-valida).
    if (aliasChanged && normalizedAlias && normalizedAlias.length < 3) {
      setError(t("auth.errAliasShort")); return;
    }
    if (wantsPassword) {
      if (!current || !next || !confirm) { setError(t("profile.passwordIncomplete")); return; }
      if (next !== confirm) { setError(t("auth.changePassword.mismatch")); return; }
      if (next.length < 6) { setError(t("auth.errPasswordShort")); return; }
    }
    if (!aliasChanged && !wantsPassword) { setError(t("profile.noChanges")); return; }

    setLoading(true);
    try {
      // Contraseña primero: si falla (actual incorrecta), no toca el alias.
      if (wantsPassword) {
        await changePassword(current, next);
        setCurrent(""); setNext(""); setConfirm("");
      }
      if (aliasChanged) await updateAlias(normalizedAlias || null);
      toast.success(t("profile.saved"));
    } catch (err: any) {
      setError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setLoading(false);
    }
  };

  const label = (text: string) => (
    <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{text}</label>
  );
  const readonly = (lbl: string, value: string) => (
    <div>{label(lbl)}<input value={value} disabled className="input-base w-full opacity-60 cursor-not-allowed" /></div>
  );
  const pwField = (lbl: string, value: string, onChange: (v: string) => void) => (
    <div>
      {label(lbl)}
      <input
        type="password" value={value} onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && save()}
        placeholder="••••••••" className="input-base w-full" aria-label={lbl}
      />
    </div>
  );

  return (
    <div className="max-w-sm mx-auto space-y-6 animate-in">
      <h1 className="font-display text-4xl text-ucl-gold">{t("profile.title")}</h1>

      <div className="card border-ucl-gold/20 p-6 space-y-4">
        {/* Alias (opcional) */}
        <h2 className="font-display text-lg">{t("profile.aliasSection")}</h2>
        {readonly(t("auth.yourTeam"), user?.team_name ?? "")}
        {readonly(t("auth.email"), user?.email ?? "")}
        <div>
          {label(t("auth.alias"))}
          <input
            type="text" value={alias} onChange={(e) => setAlias(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            placeholder={t("auth.aliasPlaceholder")} className="input-base w-full" aria-label={t("auth.alias")}
          />
          <p className="text-xs text-ucl-silver/50 mt-1.5">{t("profile.hint")}</p>
        </div>

        {/* Contraseña (dejar en blanco si no se cambia) */}
        <div className="pt-2 border-t border-ucl-blue/30">
          <h2 className="font-display text-lg mb-1">{t("auth.changePassword.title")}</h2>
          <p className="text-xs text-ucl-silver/50 mb-3">{t("profile.passwordHint")}</p>
          <div className="space-y-4">
            {pwField(t("auth.changePassword.current"), current, setCurrent)}
            {pwField(t("auth.changePassword.new"), next, setNext)}
            {pwField(t("auth.changePassword.confirm"), confirm, setConfirm)}
          </div>
        </div>

        {error && (
          <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
            {error}
          </div>
        )}

        <button onClick={save} disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
          {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("profile.save")}
        </button>
      </div>

      <button onClick={() => navigate("/")} className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm">
        {t("profile.back")}
      </button>
    </div>
  );
}
