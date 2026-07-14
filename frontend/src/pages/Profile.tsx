import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

/** Perfil del usuario logueado. Dos secciones INDEPENDIENTES (cada una con su
 *  propio botón): alias (opcional) y cambio de contraseña. */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, updateAlias, changePassword } = useAuthStore();
  const navigate = useNavigate();

  // Alias (independiente)
  const [alias, setAlias]           = useState(user?.alias ?? "");
  const [aliasError, setAliasError] = useState("");
  const [aliasLoading, setAliasLoading] = useState(false);

  // Contraseña (independiente)
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [pwError, setPwError] = useState("");
  const [pwLoading, setPwLoading] = useState(false);

  const saveAlias = async () => {
    setAliasError("");
    const trimmed = alias.trim();
    if (trimmed && trimmed.length < 3) { setAliasError(t("auth.errAliasShort")); return; }
    setAliasLoading(true);
    try {
      await updateAlias(trimmed || null);  // vacío → quita el alias
      toast.success(t("profile.aliasSaved"));
    } catch (err: any) {
      setAliasError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setAliasLoading(false);
    }
  };

  const savePassword = async () => {
    setPwError("");
    if (next !== confirm) { setPwError(t("auth.changePassword.mismatch")); return; }
    if (next.length < 6)  { setPwError(t("auth.errPasswordShort")); return; }
    setPwLoading(true);
    try {
      await changePassword(current, next);
      toast.success(t("auth.changePassword.success"));
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err: any) {
      setPwError(apiErrorMessage(err, t("auth.genericError")));
    } finally {
      setPwLoading(false);
    }
  };

  const label = (text: string) => (
    <label className="block text-xs text-ucl-silver/70 mb-1.5 font-mono uppercase">{text}</label>
  );
  const pwField = (lbl: string, value: string, onChange: (v: string) => void) => (
    <div>
      {label(lbl)}
      <input
        type="password" value={value} onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && savePassword()}
        placeholder="••••••••" className="input-base w-full" aria-label={lbl}
      />
    </div>
  );
  const errorBox = (msg: string) => (
    <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">{msg}</div>
  );

  return (
    <div className="max-w-sm mx-auto space-y-6 animate-in">
      <h1 className="font-display text-4xl text-ucl-gold">{t("profile.title")}</h1>

      {/* Sección: alias (opcional) */}
      <div className="card border-ucl-gold/20 p-6">
        <h2 className="font-display text-xl mb-1">{t("profile.aliasSection")}</h2>
        <p className="text-ucl-silver/70 text-sm mb-4">{t("profile.hint")}</p>
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
              type="text" value={alias} onChange={(e) => setAlias(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveAlias()}
              placeholder={t("auth.aliasPlaceholder")} className="input-base w-full" aria-label={t("auth.alias")}
            />
          </div>
          {aliasError && errorBox(aliasError)}
          <button onClick={saveAlias} disabled={aliasLoading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
            {aliasLoading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("profile.saveAlias")}
          </button>
        </div>
      </div>

      {/* Sección: cambiar contraseña */}
      <div className="card border-ucl-gold/20 p-6">
        <h2 className="font-display text-xl mb-4">{t("auth.changePassword.title")}</h2>
        <div className="space-y-4">
          {pwField(t("auth.changePassword.current"), current, setCurrent)}
          {pwField(t("auth.changePassword.new"), next, setNext)}
          {pwField(t("auth.changePassword.confirm"), confirm, setConfirm)}
          {pwError && errorBox(pwError)}
          <button onClick={savePassword} disabled={pwLoading} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
            {pwLoading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("auth.changePassword.submit")}
          </button>
        </div>
      </div>

      <button onClick={() => navigate("/")} className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm">
        {t("profile.back")}
      </button>
    </div>
  );
}
