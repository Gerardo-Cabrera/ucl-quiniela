import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import { apiErrorMessage } from "@/lib/apiError";
import { Spinner } from "@/components/ui";

/** Perfil del usuario logueado. Un ÚNICO botón "Guardar" aplica lo que el usuario
 *  haya tocado: el nombre de equipo y/o el alias (si los cambió) y/o la contraseña
 *  (si llenó esos campos). Los campos de contraseña vacíos = no se cambia. */
export default function ProfilePage() {
  const { t } = useTranslation();
  const { user, updateProfile, changePassword } = useAuthStore();
  const navigate = useNavigate();

  const [teamName, setTeamName] = useState(user?.team_name ?? "");
  const [alias, setAlias]     = useState(user?.alias ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext]       = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  // Validez derivada (un solo lugar): el botón se habilita solo si hay al menos un
  // cambio VÁLIDO. Los hints de cada campo guían el criterio; el backend re-valida.
  const normalizedTeam  = teamName.trim();
  const normalizedAlias = alias.trim();
  const teamChanged   = normalizedTeam  !== (user?.team_name ?? "");
  const aliasChanged  = normalizedAlias !== (user?.alias ?? "");
  const wantsPassword = Boolean(current || next || confirm);
  const passwordMismatch = Boolean(next && confirm && next !== confirm);

  const teamValid     = !teamChanged  || normalizedTeam.length >= 3;
  const aliasValid    = !aliasChanged || normalizedAlias === "" || normalizedAlias.length >= 3;
  const passwordValid = !wantsPassword || (current.length > 0 && next.length >= 6 && next === confirm);
  const canSave = (teamChanged || aliasChanged || wantsPassword) && teamValid && aliasValid && passwordValid;

  const save = async () => {
    if (!canSave || loading) return;   // el botón ya lo refleja; guarda también al pulsar Enter
    setError("");
    setLoading(true);
    try {
      // Contraseña primero: si falla (actual incorrecta), no toca el perfil.
      if (wantsPassword) {
        await changePassword(current, next);
        setCurrent(""); setNext(""); setConfirm("");
      }
      // Se envía el estado completo (equipo + alias) para no tocar el que no cambió.
      if (teamChanged || aliasChanged) {
        await updateProfile({ team_name: normalizedTeam, alias: normalizedAlias || null });
      }
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
        {/* Datos de la cuenta */}
        <h2 className="font-display text-lg">{t("profile.account")}</h2>
        <div>
          {label(t("auth.yourTeam"))}
          <input
            type="text" value={teamName} onChange={(e) => setTeamName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            placeholder={t("auth.teamPlaceholder")} className="input-base w-full" aria-label={t("auth.yourTeam")}
          />
          <p className="text-xs text-ucl-silver/50 mt-1.5">{t("profile.teamHint")}</p>
        </div>
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
          <div className="space-y-4">
            {pwField(t("auth.changePassword.current"), current, setCurrent)}
            {pwField(t("auth.changePassword.new"), next, setNext)}
            {pwField(t("auth.changePassword.confirm"), confirm, setConfirm)}
          </div>
          <p className="text-xs text-ucl-silver/50 mt-2">{t("profile.passwordHint")}</p>
          {passwordMismatch && (
            <p className="text-xs text-red-400 mt-1">{t("auth.changePassword.mismatch")}</p>
          )}
        </div>

        {error && (
          <div role="alert" className="bg-red-900/20 border border-red-500/30 rounded-lg px-4 py-2.5 text-red-400 text-sm">
            {error}
          </div>
        )}

        <button onClick={save} disabled={loading || !canSave} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
          {loading ? <><Spinner size="sm" /> {t("common.loading")}</> : t("profile.save")}
        </button>
      </div>

      <button onClick={() => navigate("/")} className="w-full text-center text-ucl-silver/60 hover:text-ucl-silver text-sm">
        {t("profile.back")}
      </button>
    </div>
  );
}
